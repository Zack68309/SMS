from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
from .models import SMSCallback
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Create your views here
def index(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')  # The phone number(s) input
        message = request.POST.get('message')  # The message input

        # Prepare the API request data
        api_url = "https://sms.nalosolutions.com/smsbackend/Resl_Nalo/send-message/"
        payload = {
            "key":  os.getenv("API_KEY"),  # Your auth key
            "msisdn": phone,  # Use the phone number(s) from the form
            "message": message,  # Use the message from the form
            "sender_id": "Test",  # Sender ID
            "callback_url": "https://9c8c-154-160-0-196.ngrok-free.app/sms-callback/"  # Add callback URL here
        }

        # Make the POST request to the SMS API
        try:
            response = requests.post(api_url, json=payload)

            # Redirect after the POST without showing any success/error message
            return redirect('index')
        except requests.exceptions.RequestException as e:
            return redirect('index')  # Redirect after POST even if there's an error

    return render(request, 'index.html')  # Render the index page


@csrf_exempt
def sms_callback(request):
    if request.method == 'POST':
        try:
            # Parse the entire JSON request body
            data = json.loads(request.body)

            # Store the callback data in the database
            SMSCallback.objects.all().delete()  # Clear old data before storing the new one

            # Create a new callback entry
            callback_entry = SMSCallback.objects.create(
                phone_number=data.get('destination', 'Unknown'),  # Assuming 'destination' is the phone number
                message=data.get('mid', 'Unknown'),  # Message ID or actual message
                status=data.get('status_desc', 'Unknown'),
                timestamp=data.get('timestamp', 'Unknown')
            )

            # Optionally store the raw callback data in session (to display in real-time without DB fetch)
            if 'callbacks' not in request.session:
                request.session['callbacks'] = []

            # Append the new callback data to the session and keep the session clean (last 1 entry)
            request.session['callbacks'] = [data]  # Only store the latest callback in session
            request.session.modified = True

            return JsonResponse({"message": "Callback received and stored successfully"}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON received"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


# Fetch the last SMS callback from the database and session
def fetch_sms_callbacks(request):
    # Fetch the latest callback from the database (since we keep only the most recent one)
    latest_callback = SMSCallback.objects.order_by('-timestamp').first()

    # Fetch session-stored callbacks
    session_callbacks = request.session.get('callbacks', [])

    # Prepare the data (both from the session and the latest DB entry)
    data = {
        "session_callbacks": session_callbacks,
        "db_callback": {
            "phone_number": latest_callback.phone_number if latest_callback else "No Data",
            "message": latest_callback.message if latest_callback else "No Data",
            "status": latest_callback.status if latest_callback else "No Data",
            "timestamp": latest_callback.timestamp if latest_callback else "No Data",
        } if latest_callback else None
    }

    return JsonResponse(data, safe=False)
