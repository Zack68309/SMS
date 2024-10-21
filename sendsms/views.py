import requests
import json
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Create your views here
def index(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')  # The phone number(s) input
        message = request.POST.get('message')  # The message input

        # Prepare the API request data
        api_url = "https://sms.nalosolutions.com/smsbackend/Resl_Nalo/send-message/"
        payload = {
            "key": "cj(@ysntf2@nx6do))9691je_)@3xn@8y2fdqzks5pn43)9d8ai4a2h3znha#l99",  # Your auth key
            "msisdn": phone,  # Use the phone number(s) from the form
            "message": message,  # Use the message from the form
            "sender_id": "Test",  # Sender ID
            "callback_url": "https://578a-154-160-0-198.ngrok-free.app/sms-callback/"  # Add callback URL here
        }

        # Make the POST request to the SMS API
        try:
            response = requests.post(api_url, json=payload)

            # Check the response status
            if response.status_code == 200:
                messages.success(request, 'Message sent successfully!')
            else:
                messages.error(request, f'Failed to send message: {response.text}')
        except requests.exceptions.RequestException as e:
            messages.error(request, f'Error: {str(e)}')

        return redirect('index')  # Redirect back to the same page after submission

    return render(request, 'index.html')  # Replace with your actual template name

# Handle the callback from the SMS service

@csrf_exempt  # Allow POST requests without CSRF token for this endpoint
def sms_callback(request):
    if request.method == 'POST':
        try:
            # Parse the JSON data
            data = json.loads(request.body)

            # Log the entire callback data received
            print("Callback data received:", data)

            return JsonResponse({"message": "Callback received successfully"}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON received"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)
