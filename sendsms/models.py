from django.db import models


class Message(models.Model):
    """One send request from the form (may target several numbers)."""

    sender_id = models.CharField(max_length=11)
    text = models.TextField()
    job_id = models.CharField(max_length=255, blank=True, db_index=True)
    # What the Nalo API said when we called it (status code + body)
    api_status_code = models.IntegerField(null=True, blank=True)
    api_response = models.TextField(blank=True)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender_id}: {self.text[:30]}"


class Recipient(models.Model):
    """A single phone number in a Message, with its latest delivery status."""

    message = models.ForeignKey(Message, related_name="recipients", on_delete=models.CASCADE)
    msisdn = models.CharField(max_length=20, db_index=True)
    mid = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=50, default="PENDING")
    network = models.CharField(max_length=50, blank=True)
    delivered_at = models.CharField(max_length=50, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.msisdn} - {self.status}"


class CallbackLog(models.Model):
    """Every raw callback Nalo posts to us, kept for debugging."""

    payload = models.JSONField()
    matched = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
