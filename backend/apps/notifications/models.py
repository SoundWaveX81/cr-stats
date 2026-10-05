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


class WarAlertPreference(models.Model):
    FREQUENCY_CHOICES = [
        (
            "hourly",
            "Cada 1 hora — 4h, 3h, 2h, 1h antes del cierre y al cierre (06:00, 07:00, 08:00, 09:00, 10:00 UTC)",
        ),
        (
            "every_2h",
            "Cada 2 horas — 4h y 2h antes del cierre y al cierre (06:00, 08:00, 10:00 UTC)",
        ),
        (
            "last_2h",
            "Últimas 2 horas — 2h y 1h antes del cierre y al cierre (08:00, 09:00, 10:00 UTC)",
        ),
        (
            "last_1h",
            "Solo última hora — 1h antes del cierre y al cierre (09:00, 10:00 UTC)",
        ),
        (
            "at_close_only",
            "Solo al cierre — 10:00 UTC (revisión y felicitación final)",
        ),
        (
            "custom",
            "Personalizado — Especificar lista de horas UTC exactas",
        ),
    ]

    clan = models.OneToOneField(
        "clans.Clan",
        on_delete=models.CASCADE,
        related_name="war_alert_preference",
        verbose_name="Clan",
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name="Alertas activadas",
        help_text="Activa o pausa las alertas automáticas de guerra para este clan.",
    )
    frequency = models.CharField(
        max_length=32,
        choices=FREQUENCY_CHOICES,
        default="hourly",
        verbose_name="Frecuencia de recordatorios",
        help_text="Frecuencia con la que se enviarán las alertas automáticas de ataques pendientes.",
    )
    custom_hours = models.CharField(
        max_length=128,
        default="6,7,8,9,10",
        blank=True,
        verbose_name="Horas UTC personalizadas",
        help_text="Aplica únicamente si se elige 'Personalizado'. Lista de horas UTC separadas por comas (ej. 6,7,8,9,10).",
    )
    silence_if_zero_pending = models.BooleanField(
        default=True,
        verbose_name="Silencio si 0 pendientes",
        help_text="Evita enviar mensajes en horas intermedias (06:00 - 09:00 UTC) si todos los miembros completaron sus ataques.",
    )
    send_congratulations_at_close = models.BooleanField(
        default=True,
        verbose_name="Felicitar al cierre si 0 pendientes",
        help_text="Envía mensaje de felicitación de 100% de asistencia a las 10:00 UTC si no hay miembros pendientes.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencia de Alertas de Guerra"
        verbose_name_plural = "Preferencias de Alertas de Guerra"
        ordering = ["clan"]

    def __str__(self) -> str:
        status = "Activas" if self.is_enabled else "Pausadas"
        return f"Alertas {self.get_frequency_display()} ({self.clan.name}) - [{status}]"

    def get_active_hours(self) -> list[int]:
        """Return the sorted list of UTC hours (0-23) during which reminders should trigger."""
        if not self.is_enabled:
            return []
        if self.frequency == "hourly":
            return [6, 7, 8, 9, 10]
        if self.frequency == "every_2h":
            return [6, 8, 10]
        if self.frequency == "last_2h":
            return [8, 9, 10]
        if self.frequency == "last_1h":
            return [9, 10]
        if self.frequency == "at_close_only":
            return [10]
        if self.frequency == "custom":
            hours = set()
            for part in self.custom_hours.split(","):
                val = part.strip()
                if val.isdigit() and 0 <= int(val) <= 23:
                    hours.add(int(val))
            return sorted(hours) if hours else [6, 7, 8, 9, 10]
        return [6, 7, 8, 9, 10]

    def should_send_at(self, dt=None) -> bool:
        """Check if alerts should trigger at the given datetime in UTC.

        Clash Royale war window runs continuously from Thursday 10:00 UTC to Monday 10:00 UTC:
        - Thursday from 10:00 UTC onwards (War Day 1)
        - Friday, Saturday, Sunday all day (War Days 1, 2, 3, 4)
        - Monday up to 10:00 UTC (War Day 4 / Colosseum final stretch)
        """
        if not self.is_enabled:
            return False
        from datetime import datetime, timezone

        now_utc = dt or datetime.now(timezone.utc)

        # 1. Hour check: must be in configured active hours for this clan
        if now_utc.hour not in self.get_active_hours():
            return False

        # 2. War window check:
        # Python weekday(): Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
        wd = now_utc.weekday()
        if wd in (4, 5, 6):  # Friday, Saturday, Sunday
            return True
        if wd == 3 and now_utc.hour >= 10:  # Thursday after 10:00 UTC
            return True
        if wd == 0 and now_utc.hour <= 10:  # Monday up to 10:00 UTC
            return True

        return False

    @classmethod
    def get_for_clan(cls, clan) -> "WarAlertPreference":
        """Retrieve preference for a clan, creating with default settings if absent."""
        pref, _ = cls.objects.get_or_create(
            clan=clan,
            defaults={
                "is_enabled": True,
                "frequency": "hourly",
                "custom_hours": "6,7,8,9,10",
                "silence_if_zero_pending": True,
                "send_congratulations_at_close": True,
            },
        )
        return pref
