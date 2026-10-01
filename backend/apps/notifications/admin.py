from django.contrib import admin

from .models import NotificationChannel


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ("clan", "provider", "is_active", "updated_at")
    list_filter = ("provider", "is_active", "clan")
    search_fields = ("clan__name", "clan__tag")
