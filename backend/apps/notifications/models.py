from django.db import models


class NotificationChannel(models.Model):
    PROVIDER_CHOICES = [
        ("console", "Consola / Logs"),
        ("discord_webhook", "Discord Webhook"),
        ("telegram", "Telegram Bot"),
    ]

    clan = models.ForeignKey(
        "clans.Clan", on_delete=models.CASCADE, related_name="notification_channels"
    )
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuración del canal (webhook_url, chat_id, token, etc.)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Canal de Notificación"
        verbose_name_plural = "Canales de Notificación"
        ordering = ["clan", "provider"]

    def __str__(self) -> str:
        return f"Canal {self.get_provider_display()} ({self.clan.name})"
