from datetime import date

import httpx
import pytest
import respx

from apps.clans.models import Clan, Member
from apps.governance.models import RosterAction
from apps.notifications.adapters import (
    ClanWarStanding,
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


@pytest.fixture
def sample_standings():
    return [
        ClanWarStanding(
            rank=1, tag="#RIVAL1", name="war 101", fame=124300, is_target=False, diff=3050
        ),
        ClanWarStanding(
            rank=2,
            tag="#NOTIF_TEST",
            name="Clan Notificaciones",
            fame=121250,
            is_target=True,
            diff=0,
        ),
        ClanWarStanding(
            rank=3, tag="#RIVAL2", name="A-15", fame=118050, is_target=False, diff=-3200
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
    def test_discord_pending_attacks_alert_with_standings(
        self, sample_clan, sample_pending_items, sample_standings
    ):
        webhook_url = "https://discord.com/api/webhooks/test/standings"
        route = respx.post(webhook_url).mock(return_value=httpx.Response(204))

        adapter = DiscordWebhookNotificationAdapter({"webhook_url": webhook_url})
        result = adapter.send_pending_attacks_alert(
            sample_clan,
            sample_pending_items,
            date(2026, 10, 5),
            hours_left=2,
            standings=sample_standings,
        )

        assert result is True
        assert route.called
        payload = route.calls.last.request.read().decode("utf-8")
        assert "Clasificación" in payload
        assert "2º de 3" in payload
        assert "121.250 pts" in payload
        assert "war 101" in payload
        assert "+3.050" in payload
        assert "A-15" in payload
        assert "-3.200" in payload

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

    @respx.mock
    def test_telegram_send_messages_with_standings(
        self, sample_clan, sample_pending_items, sample_standings
    ):
        bot_url = "https://api.telegram.org/bot12345:TEST/sendMessage"
        route = respx.post(bot_url).mock(return_value=httpx.Response(200, json={"ok": True}))

        adapter = TelegramNotificationAdapter(
            {
                "bot_token": "12345:TEST",
                "chat_id": "-100123456789",
            }
        )

        assert (
            adapter.send_pending_attacks_alert(
                sample_clan,
                sample_pending_items,
                date(2026, 10, 5),
                hours_left=1,
                standings=sample_standings,
            )
            is True
        )
        assert route.called
        call_json = route.calls.last.request.read().decode("utf-8")
        assert "Posición en Guerra: 🥈 2º de 3" in call_json
        assert "121.250 pts" in call_json
        assert "a 3.050 pts del 1º (war 101)" in call_json
        assert "war 101" in call_json
        assert "+3.050" in call_json
        assert "A-15" in call_json
        assert "-3.200" in call_json


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

    def test_war_alert_preference_frequencies(self, sample_clan):
        from datetime import datetime, timezone

        from apps.notifications.models import WarAlertPreference

        pref = WarAlertPreference.get_for_clan(sample_clan)
        assert pref.is_enabled is True
        assert pref.frequency == "hourly"
        assert pref.get_active_hours() == [6, 7, 8, 9, 10]

        # On a Sunday at 08:00 UTC (Sunday is weekday 6)
        sunday_8am = datetime(2026, 10, 4, 8, 0, tzinfo=timezone.utc)
        assert pref.should_send_at(sunday_8am) is True

        # On a Monday at 08:00 UTC (weekday 0, before 10:00 UTC - War Day 4 / Colosseum final stretch)
        monday_8am = datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc)
        assert pref.should_send_at(monday_8am) is True

        # On a Monday at 12:00 UTC (weekday 0, after 10:00 UTC - Training Day 1 started)
        monday_12pm = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
        assert pref.should_send_at(monday_12pm) is False

        # On a Thursday at 08:00 UTC (weekday 3, before 10:00 UTC - Training Day 3 final stretch, war hasn't started)
        thursday_8am = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
        assert pref.should_send_at(thursday_8am) is False

        # On a Wednesday (weekday 2 - training day)
        wednesday_8am = datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc)
        assert pref.should_send_at(wednesday_8am) is False

        # Every 2 hours
        pref.frequency = "every_2h"
        assert pref.get_active_hours() == [6, 8, 10]
        assert pref.should_send_at(datetime(2026, 10, 4, 7, 0, tzinfo=timezone.utc)) is False
        assert pref.should_send_at(datetime(2026, 10, 4, 8, 0, tzinfo=timezone.utc)) is True

        # Custom hours
        pref.frequency = "custom"
        pref.custom_hours = "7, 12, 20"
        assert pref.get_active_hours() == [7, 12, 20]
        assert pref.should_send_at(datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)) is True
        assert pref.should_send_at(datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)) is False
        # Thursday afternoon at 12:00 UTC (War Day 1 is running)
        assert pref.should_send_at(datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)) is True

        # Disabled
        pref.is_enabled = False
        assert pref.get_active_hours() == []
        assert pref.should_send_at(datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)) is False
