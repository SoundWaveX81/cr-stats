from datetime import date, timedelta

import httpx
import pytest
import respx
from django.test import override_settings
from rest_framework import status

from apps.bot.dispatcher import TelegramCommandDispatcher
from apps.clans.models import Clan, Member, WarPass
from apps.governance.models import RosterAction
from apps.wars.models import RiverRace, WarAttackLog, WarDay


@pytest.fixture
def sample_clan():
    clan = Clan.objects.create(
        tag="#2PP",
        name="Furia Roja",
        medal_threshold=2000,
        war_day_reset_time="10:00:00",
        is_active=True,
    )
    Member.objects.create(clan=clan, tag="#M1", name="Lider Supremo", role="leader")
    Member.objects.create(clan=clan, tag="#M2", name="Guerrero Furia", role="elder")
    Member.objects.create(clan=clan, tag="#M3", name="Recluta Novato", role="member")
    return clan


@pytest.mark.django_db
class TestBotCommands:
    def test_cmd_help(self):
        dispatcher = TelegramCommandDispatcher()
        reply = dispatcher.dispatch("/ayuda")
        assert "CR Total" in reply
        assert "/estado" in reply
        assert "/pendientes" in reply
        assert "/sanciones" in reply

        # /start should also return help
        reply_start = dispatcher.dispatch("/start")
        assert "CR Total" in reply_start

    def test_cmd_estado(self, sample_clan):
        RiverRace.objects.create(
            clan=sample_clan,
            season_id=2026,
            section_index=2,
            state="matched",
            clan_score=15400,
        )

        dispatcher = TelegramCommandDispatcher()
        reply = dispatcher.dispatch("/estado #2PP")

        assert "Furia Roja" in reply
        assert "#2PP" in reply
        assert "15,400" in reply
        assert "Semana 2" in reply

    def test_cmd_pendientes_with_and_without_war_pass(self, sample_clan):
        today = date.today()
        race = RiverRace.objects.create(
            clan=sample_clan, season_id=2026, section_index=1, state="matched"
        )
        war_day = WarDay.objects.create(
            river_race=race,
            day_type="war",
            day_index=1,
            date=today,
            is_closed=False,
        )

        m1 = sample_clan.members.get(tag="#M1")
        m2 = sample_clan.members.get(tag="#M2")
        m3 = sample_clan.members.get(tag="#M3")

        # m1 did 4 attacks (completed)
        WarAttackLog.objects.create(war_day=war_day, member=m1, attacks_used=4, medals_earned=900)
        # m2 did 1 attack (pending 3)
        WarAttackLog.objects.create(war_day=war_day, member=m2, attacks_used=1, medals_earned=200)
        # m3 has an active WarPass
        WarPass.objects.create(
            member=m3,
            reason="Examen médico",
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
        )

        dispatcher = TelegramCommandDispatcher()
        reply = dispatcher.dispatch("/pendientes #2PP")

        assert "Ataques Pendientes Hoy" in reply
        assert "Guerrero Furia" in reply
        assert "Restan <b>3</b> ataques" in reply
        # m1 is completed and m3 is excused, so neither should appear in pending
        assert "Lider Supremo" not in reply
        assert "Recluta Novato" not in reply

    def test_cmd_sanciones_and_resolution(self, sample_clan):
        m2 = sample_clan.members.get(tag="#M2")
        action = RosterAction.objects.create(
            clan=sample_clan,
            member=m2,
            action_type="demote_member",
            reason="0/4 ataques de guerra en jornada",
        )

        dispatcher = TelegramCommandDispatcher()

        # Check list
        reply_list = dispatcher.dispatch("/sanciones")
        assert f"[ID {action.id}]" in reply_list
        assert "Guerrero Furia" in reply_list

        # Execute action
        reply_exec = dispatcher.dispatch(f"/ejecutar {action.id}")
        assert "ejecutada con éxito" in reply_exec
        action.refresh_from_db()
        assert action.status == "executed"

        # Create another action and dismiss it
        action2 = RosterAction.objects.create(
            clan=sample_clan,
            member=m2,
            action_type="kick",
            reason="Inasistencia reiterada",
        )
        reply_dismiss = dispatcher.dispatch(f"/descartar {action2.id}")
        assert "descartada" in reply_dismiss
        action2.refresh_from_db()
        assert action2.status == "dismissed"

    def test_cmd_exentar(self, sample_clan):
        dispatcher = TelegramCommandDispatcher()
        reply = dispatcher.dispatch("/exentar #M2 5 Viaje de trabajo y mudanza")

        assert "Pase de Guerra Otorgado con Éxito" in reply
        assert "Guerrero Furia" in reply
        assert "5 días" in reply

        m2 = sample_clan.members.get(tag="#M2")
        pass_obj = m2.war_passes.first()
        assert pass_obj is not None
        assert pass_obj.reason == "Viaje de trabajo y mudanza"
        assert pass_obj.end_date == date.today() + timedelta(days=5)

    @respx.mock
    def test_cmd_sync(self):
        import json
        from pathlib import Path

        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        clan_payload = json.loads((fixtures_dir / "clan_response.json").read_text())
        race_payload = json.loads((fixtures_dir / "currentriverrace_response.json").read_text())

        respx.get("https://api.clashroyale.com/v1/clans/%232PP").mock(
            return_value=httpx.Response(200, json=clan_payload)
        )
        respx.get("https://api.clashroyale.com/v1/clans/%232PP/currentriverrace").mock(
            return_value=httpx.Response(200, json=race_payload)
        )

        dispatcher = TelegramCommandDispatcher()
        reply = dispatcher.dispatch("/sincronizar #2PP")
        assert "¡Sincronización Exitosa!" in reply
        assert "Furia Roja" in reply
        assert Clan.objects.filter(tag="#2PP").exists()

    def test_unknown_command(self):
        dispatcher = TelegramCommandDispatcher()
        reply = dispatcher.dispatch("/inventado")
        assert "no reconocido" in reply


@pytest.mark.django_db
class TestTelegramWebhookView:
    @override_settings(TELEGRAM_BOT_SECRET_TOKEN="my-super-secret-token")
    def test_webhook_rejects_invalid_secret(self, api_client):
        response = api_client.post(
            "/api/bot/telegram/webhook/",
            data={"message": {"text": "/ayuda"}},
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong-token",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @override_settings(
        TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        TELEGRAM_BOT_SECRET_TOKEN="my-super-secret-token",
    )
    @respx.mock
    def test_webhook_receives_and_replies_via_api(self, api_client, sample_clan):
        route = respx.post(
            "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage"
        ).mock(return_value=httpx.Response(200, json={"ok": True}))

        payload = {
            "update_id": 10001,
            "message": {
                "message_id": 42,
                "from": {"id": 99999, "first_name": "Lider"},
                "chat": {"id": 88888, "type": "supergroup"},
                "text": "/ayuda",
            },
        }

        response = api_client.post(
            "/api/bot/telegram/webhook/",
            data=payload,
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="my-super-secret-token",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}
        assert route.called
        sent_body = route.calls.last.request.read().decode("utf-8")
        assert "CR Total" in sent_body
        assert "88888" in sent_body
