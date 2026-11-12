from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("sms-callback/", views.sms_callback, name="sms_callback"),
    path("api/messages/", views.message_history, name="message_history"),
]
