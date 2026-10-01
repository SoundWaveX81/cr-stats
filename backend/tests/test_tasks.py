import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from apps.clans.models import Clan, Member, WarPass
from apps.governance.models import RosterAction
from apps.governance.tasks import task_evaluate_war_day_governance
from apps.ingestion.tasks import task_send_pending_attack_reminders, task_sync_clan_data
from apps.wars.models import RiverRace, WarAttackLog, WarDay

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> dict:
    return json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))


@pytest.mark.django_db
class TestCeleryTasks:
    @respx.mock
    def test_task_sync_clan_data(self):
        clan = Clan.objects.create(tag="#2PP", name="Furia Antigua")
        clan_payload = load_fixture("clan_response.json")
        race_payload = load_fixture("currentriverrace_response.json")

        respx.get("https://api.clashroyale.com/v1/clans/%232PP").mock(
            return_value=httpx.Response(200, json=clan_payload)
        )
        respx.get("https://api.clashroyale.com/v1/clans/%232PP/currentriverrace").mock(
            return_value=httpx.Response(200, json=race_payload)
        )

        synced = task_sync_clan_data.apply(args=["#2PP"]).get()
        assert synced == 1

        clan.refresh_from_db()
        assert clan.name == "Furia Roja"
        assert clan.members.count() == 5
        assert RiverRace.objects.filter(clan=clan).exists()

    def test_task_send_pending_attack_reminders(self):
        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        m1 = Member.objects.create(clan=clan, tag="#M1", name="Player 1", role="member")
        m2 = Member.objects.create(clan=clan, tag="#M2", name="Player 2 (Excused)", role="member")
        m3 = Member.objects.create(clan=clan, tag="#M3", name="Player 3 (Completed)", role="elder")

        today = date.today()
        # Excused pass for m2
        WarPass.objects.create(
            member=m2,
            reason="Médico",
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
        )

        race = RiverRace.objects.create(clan=clan, season_id=2026, section_index=1)
        war_day = WarDay.objects.create(
            river_race=race,
            day_type="war",
            day_index=1,
            date=today,
            is_closed=False,
        )

        # m3 completed all 4 attacks
        WarAttackLog.objects.create(
            war_day=war_day,
            member=m3,
            attacks_used=4,
            medals_earned=900,
        )
        # m1 completed only 2 attacks
        WarAttackLog.objects.create(
            war_day=war_day,
            member=m1,
            attacks_used=2,
            medals_earned=400,
        )

        with patch(
            "apps.ingestion.tasks.NotificationDispatcher.dispatch_pending_attacks"
        ) as mock_dispatch:
            summary = task_send_pending_attack_reminders.apply().get()

            assert summary.get("#2PP") == 1
            mock_dispatch.assert_called_once()
            args, _ = mock_dispatch.call_args
            pending_items = args[1]
            assert len(pending_items) == 1
            assert pending_items[0].member_tag == "#M1"
            assert pending_items[0].remaining_attacks == 2

    def test_task_evaluate_war_day_governance(self):
        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        m1 = Member.objects.create(clan=clan, tag="#M1", name="Player 1", role="member")
        race = RiverRace.objects.create(clan=clan, season_id=2026, section_index=1)
        war_day = WarDay.objects.create(
            river_race=race,
            day_type="war",
            day_index=1,
            date=date.today() - timedelta(days=1),
            is_closed=False,
        )
        # m1 did only 1 attack (fails 4 attack requirement)
        WarAttackLog.objects.create(
            war_day=war_day,
            member=m1,
            attacks_used=1,
            medals_earned=200,
        )

        with patch("apps.governance.tasks.NotificationDispatcher.dispatch_roster_report"):
            total_actions = task_evaluate_war_day_governance.apply(args=["#2PP"]).get()

            assert total_actions == 1
            war_day.refresh_from_db()
            assert war_day.is_closed is True

            actions = RosterAction.objects.filter(clan=clan, member=m1)
            assert actions.count() == 1
            assert actions.first().action_type == "kick"
