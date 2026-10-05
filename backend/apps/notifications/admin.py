from django.contrib import admin, messages

from apps.notifications.dispatcher import NotificationDispatcher

from .models import NotificationChannel, WarAlertPreference


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ("clan", "provider", "is_active", "updated_at")
    list_filter = ("provider", "is_active", "clan")
    search_fields = ("clan__name", "clan__tag")
    readonly_fields = ("created_at", "updated_at")
    actions = ["send_test_message", "force_pending_attacks_alert"]

    fieldsets = (
        (
            None,
            {
                "fields": ("clan", "provider", "is_active"),
            },
        ),
        (
            "Configuración Técnica (JSON)",
            {
                "fields": ("config",),
                "description": (
                    "Estructura JSON requerida según el proveedor seleccionado:<br/>"
                    '• <b>Telegram Bot</b>: <code>{"chat_id": "-1001234567890"}</code> '
                    '(<i>opcional:</i> <code>"bot_token": "123456:ABC..."</code> si deseas usar un bot distinto al general en .env)<br/>'
                    '• <b>Discord Webhook</b>: <code>{"webhook_url": "https://discord.com/api/webhooks/..."}</code><br/>'
                    "• <b>Consola / Logs</b>: <code>{}</code>"
                ),
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description="🔔 Enviar mensaje de prueba a los canales seleccionados")
    def send_test_message(self, request, queryset):
        successes = []
        failures = []
        for channel in queryset:
            adapter = NotificationDispatcher.get_adapter(channel)
            if not adapter:
                failures.append(f"{channel} (proveedor desconocido)")
                continue
            try:
                ok = adapter.send_test_message(channel.clan)
                if ok:
                    successes.append(str(channel))
                else:
                    failures.append(str(channel))
            except Exception as exc:
                failures.append(f"{channel}: {exc}")

        if successes:
            self.message_user(
                request,
                f"✅ Mensaje de prueba enviado exitosamente a: {', '.join(successes)}",
                level=messages.SUCCESS,
            )
        if failures:
            self.message_user(
                request,
                f"❌ Error al enviar mensaje a: {', '.join(failures)}",
                level=messages.ERROR,
            )

    @admin.action(description="⚠️ Forzar envío de alerta de ataques pendientes ahora")
    def force_pending_attacks_alert(self, request, queryset):
        from datetime import date

        from apps.ingestion.services.sync_river_race import SyncRiverRaceService
        from apps.notifications.adapters.base import PendingAttackItem
        from apps.wars.models import WarAttackLog, WarDay

        successes = []
        failures = []
        sync_race_service = SyncRiverRaceService()
        synced_clans = set()
        today = date.today()

        for channel in queryset:
            clan = channel.clan
            adapter = NotificationDispatcher.get_adapter(channel)
            if not adapter:
                failures.append(f"{channel} (proveedor desconocido)")
                continue

            if clan.tag not in synced_clans:
                try:
                    sync_race_service.sync(clan)
                    synced_clans.add(clan.tag)
                except Exception as exc:
                    self.message_user(
                        request,
                        f"Aviso de sincronización para {clan.name}: {exc}",
                        level=messages.WARNING,
                    )

            open_war_day = (
                WarDay.objects.filter(
                    river_race__clan=clan, day_type="war", is_closed=False, date=today
                ).first()
                or WarDay.objects.filter(river_race__clan=clan, day_type="war")
                .order_by("-date")
                .first()
            )

            if not open_war_day:
                failures.append(f"{channel} (no hay jornada de guerra registrada)")
                continue

            active_members = clan.members.filter(is_active=True)
            attack_logs = {
                log.member_id: log for log in WarAttackLog.objects.filter(war_day=open_war_day)
            }

            pending_items = []
            for member in active_members:
                has_pass = member.war_passes.filter(
                    start_date__lte=open_war_day.date,
                    end_date__gte=open_war_day.date,
                ).exists()
                if has_pass:
                    continue

                log = attack_logs.get(member.tag)
                used = log.attacks_used if log else 0
                if used < 4:
                    pending_items.append(
                        PendingAttackItem(
                            member_tag=member.tag,
                            member_name=member.name,
                            role=member.role,
                            attacks_used=used,
                            remaining_attacks=4 - used,
                            reliability_score=float(member.reliability_score),
                        )
                    )

            try:
                if pending_items:
                    ok = adapter.send_pending_attacks_alert(
                        clan, pending_items, open_war_day.date, hours_left=0
                    )
                else:
                    ok = adapter.send_all_attacks_completed_alert(clan, open_war_day.date)

                if ok:
                    successes.append(str(channel))
                else:
                    failures.append(str(channel))
            except Exception as exc:
                failures.append(f"{channel}: {exc}")

        if successes:
            self.message_user(
                request,
                f"🚀 Alerta de ataques enviada exitosamente a: {', '.join(successes)}",
                level=messages.SUCCESS,
            )
        if failures:
            self.message_user(
                request,
                f"❌ Error al enviar alerta a: {', '.join(failures)}",
                level=messages.ERROR,
            )


@admin.register(WarAlertPreference)
class WarAlertPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "clan",
        "frequency",
        "is_enabled",
        "silence_if_zero_pending",
        "send_congratulations_at_close",
        "updated_at",
    )
    list_filter = (
        "is_enabled",
        "frequency",
        "silence_if_zero_pending",
        "send_congratulations_at_close",
    )
    search_fields = ("clan__name", "clan__tag")
    readonly_fields = ("created_at", "updated_at", "display_active_hours")

    fieldsets = (
        (
            "Configuración del Clan",
            {
                "fields": ("clan", "is_enabled"),
                "description": "Control principal para activar o pausar recordatorios automáticos de ataques de guerra.",
            },
        ),
        (
            "Frecuencia y Horarios",
            {
                "fields": ("frequency", "custom_hours", "display_active_hours"),
                "description": (
                    "Elige la frecuencia deseada para los días de guerra (Jueves 10:00 UTC a Lunes 10:00 UTC).<br/>"
                    "• <b>Cada 1 hora:</b> 06:00, 07:00, 08:00, 09:00 y 10:00 UTC (4h, 3h, 2h, 1h antes del cierre y al cierre).<br/>"
                    "• <b>Cada 2 horas:</b> 06:00, 08:00 y 10:00 UTC (4h y 2h antes del cierre y al cierre).<br/>"
                    "• <b>Últimas 2 horas:</b> 08:00, 09:00 y 10:00 UTC (2h y 1h antes del cierre y al cierre).<br/>"
                    "• <b>Solo última hora:</b> 09:00 y 10:00 UTC (1h antes del cierre y al cierre).<br/>"
                    "• <b>Solo al cierre:</b> 10:00 UTC.<br/>"
                    "• <b>Personalizado:</b> Introduce las horas UTC deseadas separadas por comas en el campo inferior."
                ),
            },
        ),
        (
            "Comportamiento ante 0 Pendientes",
            {
                "fields": ("silence_if_zero_pending", "send_congratulations_at_close"),
                "description": "Reglas para silenciar spam intermedio o felicitar al clan al cierre de jornada.",
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Horas UTC activas calculadas")
    def display_active_hours(self, obj):
        hours = obj.get_active_hours()
        if not hours:
            return "Ninguna (Alertas desactivadas)"
        return ", ".join(f"{h:02d}:00 UTC" for h in hours)
