from django.db import models

# Create your models here.
from django.db import models

class SMSCallback(models.Model):
    phone_number = models.CharField(max_length=15)  # Phone number of the recipient
    message = models.TextField()  # Store the message ID or content
    status = models.CharField(max_length=50)  # Delivery status (e.g., DELIVRD)
    timestamp = models.DateTimeField(auto_now_add=True)  # Automatically set to now when created

    def __str__(self):
        return f"{self.phone_number} - {self.status} at {self.timestamp}"
