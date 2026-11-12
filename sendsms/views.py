import json
import logging
import re

import requests
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import CallbackLog, Message, Recipient

logger = logging.getLogger(__name__)

MSISDN_RE = re.compile(r"^\d{10,15}$")


def normalize_msisdn(raw):
    """Turn '024 412 3456' or '+233244123456' into '233244123456'."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10 and digits.startswith("0"):
        digits = settings.DEFAULT_COUNTRY_CODE + digits[1:]
    return digits


def callback_url_for(request):
    """Public URL Nalo should post delivery reports to.

    Uses CALLBACK_BASE_URL when set; otherwise the address the page was opened
    on, which works automatically behind a Cloudflare/ngrok tunnel.
    """
    path = reverse("sms_callback")
    if settings.CALLBACK_BASE_URL:
        return settings.CALLBACK_BASE_URL.rstrip("/") + path
    return request.build_absolute_uri(path)


def is_public(url):
    return not re.match(r"^https?://(localhost|127\.|0\.0\.0\.0|\[::1\])", url)


def index(request):
    if request.method == "POST":
        return send_sms(request)

    callback_url = callback_url_for(request)
    return render(
        request,
        "index.html",
        {
            "sender_ids": settings.SENDER_IDS,
            "callback_url": callback_url,
            "callback_public": is_public(callback_url),
            "api_key_set": bool(settings.SMS_API_KEY),
        },
    )


def send_sms(request):
    sender_id = request.POST.get("sender_id", "").strip()
    text = request.POST.get("message", "").strip()
    raw_numbers = [n for n in re.split(r"[,\s;]+", request.POST.get("phone", "")) if n]
    numbers = list(dict.fromkeys(normalize_msisdn(n) for n in raw_numbers))

    errors = []
    if sender_id not in settings.SENDER_IDS:
        errors.append("Choose a sender ID from the list.")
    if not text:
        errors.append("Message cannot be empty.")
    if not numbers:
        errors.append("Enter at least one phone number.")
    bad = [n for n in numbers if not MSISDN_RE.match(n)]
    if bad:
        errors.append(f"Invalid phone number(s): {', '.join(bad)}. Use e.g. 233244123456.")
    if not settings.SMS_API_KEY:
        errors.append("SMS_API_KEY is not set on the server.")
    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect("index")

    with transaction.atomic():
        msg = Message.objects.create(sender_id=sender_id, text=text)
        Recipient.objects.bulk_create(Recipient(message=msg, msisdn=n) for n in numbers)

    payload = {
        "key": settings.SMS_API_KEY,
        "msisdn": ",".join(numbers),
        "message": text,
        "sender_id": sender_id,
        "callback_url": callback_url_for(request),
    }
    try:
        resp = requests.post(settings.SMS_API_URL, json=payload, timeout=20)
        msg.api_status_code = resp.status_code
        msg.api_response = resp.text[:2000]
        try:
            body = resp.json()
        except ValueError:
            body = {}
        msg.job_id = str(body.get("job_id", "")) if isinstance(body, dict) else ""
        msg.accepted = resp.ok and isinstance(body, dict) and str(body.get("status")) == "1701"
    except requests.RequestException as exc:
        logger.exception("SMS API call failed")
        msg.api_response = f"Request failed: {exc}"
    msg.save()

    if msg.accepted:
        messages.success(request, f"Accepted by Nalo for {len(numbers)} number(s). Job ID: {msg.job_id}")
    else:
        msg.recipients.update(status="FAILED")
        messages.error(request, f"Nalo rejected the request ({msg.api_status_code}): {msg.api_response}")
    return redirect("index")


@csrf_exempt
@require_POST
def sms_callback(request):
    """Receives both kinds of Nalo callbacks.

    1. Submission result: {"status": "1714", "job_id": ..., "msisdn": ...} or an error.
    2. Delivery report (DLR): {"mid", "destination", "status_desc", "network", "deliv_date", ...}
    """
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        data = request.POST.dict()
    if not isinstance(data, dict) or not data:
        return JsonResponse({"error": "Expected a JSON object"}, status=400)

    log = CallbackLog.objects.create(payload=data)
    matched = False

    if data.get("mid") or data.get("status_desc"):
        matched = _apply_dlr(data)
    elif data.get("job_id"):
        matched = _apply_submission(data)

    if matched:
        log.matched = True
        log.save(update_fields=["matched"])
    return JsonResponse({"received": True, "matched": matched})


def _apply_dlr(data):
    mid = str(data.get("mid", ""))
    msisdn = normalize_msisdn(str(data.get("destination") or data.get("msisdn") or ""))
    status = str(data.get("status_desc") or data.get("status") or "UNKNOWN")

    recipient = Recipient.objects.filter(mid=mid).first() if mid else None
    if recipient is None and msisdn:
        # DLRs don't carry our job_id, so match the newest unreported send to this number.
        recipient = (
            Recipient.objects.filter(msisdn=msisdn, mid="")
            .order_by("-message__created_at")
            .first()
        ) or Recipient.objects.filter(msisdn=msisdn).order_by("-message__created_at").first()
    if recipient is None:
        return False

    recipient.mid = mid or recipient.mid
    recipient.status = status
    recipient.network = str(data.get("network", ""))[:50]
    recipient.delivered_at = str(data.get("deliv_date") or data.get("delivery_date") or "")[:50]
    recipient.save()
    return True


def _apply_submission(data):
    msg = Message.objects.filter(job_id=str(data["job_id"])).first()
    if msg is None:
        return False
    if str(data.get("status")) == "1714":
        msg.recipients.filter(status="PENDING").update(status="SUBMITTED")
    else:
        msg.recipients.filter(status="PENDING").update(status="REJECTED")
    return True


@require_GET
def message_history(request):
    rows = []
    for m in Message.objects.prefetch_related("recipients")[:50]:
        for r in m.recipients.all():
            rows.append(
                {
                    "created_at": m.created_at.isoformat(),
                    "sender_id": m.sender_id,
                    "text": m.text,
                    "msisdn": r.msisdn,
                    "status": r.status,
                    "network": r.network,
                    "delivered_at": r.delivered_at,
                    "mid": r.mid,
                }
            )
    return JsonResponse({"messages": rows})
