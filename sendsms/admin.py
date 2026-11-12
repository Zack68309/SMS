from django.contrib import admin

from .models import CallbackLog, Message, Recipient


class RecipientInline(admin.TabularInline):
    model = Recipient
    extra = 0


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "sender_id", "text", "accepted", "job_id")
    inlines = [RecipientInline]


@admin.register(CallbackLog)
class CallbackLogAdmin(admin.ModelAdmin):
    list_display = ("received_at", "matched", "payload")
