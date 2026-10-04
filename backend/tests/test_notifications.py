from datetime import date

import httpx
import pytest
import respx

from apps.clans.models import Clan, Member
from apps.governance.models import RosterAction
from apps.notifications.adapters import (
    ConsoleNotificationAdapter,
    DiscordWebhookNotificationAdapter,
    PendingAttackItem,
    TelegramNotificationAdapter,
)
from apps.notifications.dispatcher import NotificationDispatcher
from apps.notifications.models import NotificationChannel

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample_clan():
    return Clan.objects.create(tag="#NOTIF_TEST", name="Clan Notificaciones")


@pytest.fixture
def sample_pending_items():
    return [
        PendingAttackItem(
            member_tag="#P1",
            member_name="Pekka Fuerte",
            role="member",
            attacks_used=1,
            remaining_attacks=3,
        ),
        PendingAttackItem(
            member_tag="#P2",
            member_name="Mago Eléctrico",
            role="elder",
            attacks_used=0,
            remaining_attacks=4,
        ),
    ]


class TestConsoleNotificationAdapter:
    def test_console_methods(self, sample_clan, sample_pending_items):
        adapter = ConsoleNotificationAdapter()
        today = date.today()

        assert adapter.send_pending_attacks_alert(sample_clan, sample_pending_items, today) is True

        member = Member.objects.create(tag="#M1", clan=sample_clan, name="Guerrero")
        action = RosterAction.objects.create(
            clan=sample_clan,
            member=member,
            action_type="demote_member",
            reason="Falta de ataques",
        )
        assert adapter.send_daily_roster_report(sample_clan, [action], today) is True
        assert adapter.send_leadership_notice(sample_clan, [action]) is True


class TestDiscordWebhookNotificationAdapter:
    @respx.mock
    def test_discord_pending_attacks_alert(self, sample_clan, sample_pending_items):
        webhook_url = "https://discord.com/api/webhooks/test/123"
        route = respx.post(webhook_url).mock(return_value=httpx.Response(204))

        adapter = DiscordWebhookNotificationAdapter({"webhook_url": webhook_url})
        result = adapter.send_pending_attacks_alert(
            sample_clan, sample_pending_items, date(2026, 9, 30)
        )

        assert result is True
        assert route.called
        payload = route.calls.last.request.read().decode("utf-8")
        assert "Ataques Pendientes" in payload
        assert "Pekka Fuerte" in payload
        assert "Mago Eléctrico" in payload

        # Test with high risk item and countdown
        high_risk_item = PendingAttackItem(
            member_tag="#HR",
            member_name="Riesgo Man",
            role="member",
            attacks_used=0,
            remaining_attacks=4,
            reliability_score=35.0,
        )
        assert (
            adapter.send_pending_attacks_alert(
                sample_clan, [high_risk_item], date(2026, 9, 30), hours_left=3
            )
            is True
        )
        payload_hr = route.calls.last.request.read().decode("utf-8")
        assert "Candidatos a Reemplazo" in payload_hr
        assert "3 horas" in payload_hr

        # Test all attacks completed
        assert adapter.send_all_attacks_completed_alert(sample_clan, date(2026, 9, 30)) is True
        payload_comp = route.calls.last.request.read().decode("utf-8")
        assert "100% de Asistencia Completado" in payload_comp

    @respx.mock
    def test_discord_daily_report_with_kicks(self, sample_clan):
        webhook_url = "https://discord.com/api/webhooks/test/123"
        route = respx.post(webhook_url).mock(return_value=httpx.Response(204))

        member = Member.objects.create(tag="#MKICK", clan=sample_clan, name="Inactivo")
        action = RosterAction.objects.create(
            clan=sample_clan,
            member=member,
            action_type="kick",
            reason="0 de 4 ataques completados",
        )

        adapter = DiscordWebhookNotificationAdapter({"webhook_url": webhook_url})
        result = adapter.send_daily_roster_report(sample_clan, [action], date(2026, 9, 30))

        assert result is True
        assert route.called
        data = respx.calls.last.request.read().decode("utf-8")
        assert "Reporte de Gobernanza" in data
        assert "15158332" in data  # Red color for kick


class TestTelegramNotificationAdapter:
    @respx.mock
    def test_telegram_send_messages(self, sample_clan, sample_pending_items):
        bot_url = "https://api.telegram.org/bot12345:TEST/sendMessage"
        route = respx.post(bot_url).mock(return_value=httpx.Response(200, json={"ok": True}))

        adapter = TelegramNotificationAdapter(
            {
                "bot_token": "12345:TEST",
                "chat_id": "-100123456789",
            }
        )

        # Test pending attacks alert
        assert (
            adapter.send_pending_attacks_alert(sample_clan, sample_pending_items, date(2026, 9, 30))
            is True
        )
        assert route.called
        call_json = route.calls.last.request.read().decode("utf-8")
        assert "-100123456789" in call_json
        assert "Recordatorio de Ataques de Guerra" in call_json

        # Test all attacks completed
        assert adapter.send_all_attacks_completed_alert(sample_clan, date(2026, 9, 30)) is True
        call_comp = route.calls.last.request.read().decode("utf-8")
        assert "100% de Asistencia Completado" in call_comp


@pytest.mark.django_db
class TestNotificationDispatcher:
    @respx.mock
    def test_dispatcher_fanout_across_multiple_channels(self, sample_clan, sample_pending_items):
        discord_url = "https://discord.com/api/webhooks/fanout/123"
        telegram_url = "https://api.telegram.org/botFANOUT:TEST/sendMessage"

        respx.post(discord_url).mock(return_value=httpx.Response(204))
        respx.post(telegram_url).mock(return_value=httpx.Response(200, json={"ok": True}))

        ch_console = NotificationChannel.objects.create(
            clan=sample_clan, provider="console", config={}
        )
        ch_discord = NotificationChannel.objects.create(
            clan=sample_clan, provider="discord_webhook", config={"webhook_url": discord_url}
        )
        ch_telegram = NotificationChannel.objects.create(
            clan=sample_clan,
            provider="telegram",
            config={"bot_token": "FANOUT:TEST", "chat_id": "12345"},
        )

        dispatcher = NotificationDispatcher()
        results = dispatcher.dispatch_pending_attacks(
            sample_clan, sample_pending_items, date(2026, 9, 30)
        )

        assert len(results) == 3
        assert results[ch_console.id] is True
        assert results[ch_discord.id] is True
        assert results[ch_telegram.id] is True

    @respx.mock
    def test_dispatcher_fault_tolerance_when_one_channel_fails(
        self, sample_clan, sample_pending_items
    ):
        broken_discord_url = "https://discord.com/api/webhooks/broken/500"
        respx.post(broken_discord_url).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        ch_broken = NotificationChannel.objects.create(
            clan=sample_clan, provider="discord_webhook", config={"webhook_url": broken_discord_url}
        )
        ch_console = NotificationChannel.objects.create(
            clan=sample_clan, provider="console", config={}
        )

        dispatcher = NotificationDispatcher()
        results = dispatcher.dispatch_pending_attacks(
            sample_clan, sample_pending_items, date(2026, 9, 30)
        )

        # El canal con error falla pero el canal de consola procesa con éxito
        assert results[ch_broken.id] is False
        assert results[ch_console.id] is True

    @respx.mock
    def test_send_test_message_methods(self, sample_clan):
        discord_url = "https://discord.com/api/webhooks/test/testmsg"
        telegram_url = "https://api.telegram.org/botTOKEN:TEST/sendMessage"

        respx.post(discord_url).mock(return_value=httpx.Response(204))
        respx.post(telegram_url).mock(return_value=httpx.Response(200, json={"ok": True}))

        console_adapter = ConsoleNotificationAdapter()
        assert console_adapter.send_test_message(sample_clan) is True

        discord_adapter = DiscordWebhookNotificationAdapter({"webhook_url": discord_url})
        assert discord_adapter.send_test_message(sample_clan) is True

        telegram_adapter = TelegramNotificationAdapter(
            {"bot_token": "TOKEN:TEST", "chat_id": "9999"}
        )
        assert telegram_adapter.send_test_message(sample_clan) is True

    @respx.mock
    def test_management_command_test_notifications(self, sample_clan):
        from django.core.management import call_command

        discord_url = "https://discord.com/api/webhooks/test/cmd"
        respx.post(discord_url).mock(return_value=httpx.Response(204))

        NotificationChannel.objects.create(
            clan=sample_clan, provider="discord_webhook", config={"webhook_url": discord_url}
        )

        call_command("test_notifications", clan=sample_clan.tag)
