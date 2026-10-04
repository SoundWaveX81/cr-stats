import json
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest
import respx
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from apps.clans.models import Clan, Member
from apps.governance.models import RosterAction
from apps.wars.models import RiverRace, WarAttackLog, WarDay

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> dict:
    return json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))


@pytest.fixture
def auth_user():
    return User.objects.create_user(username="clan_leader", password="secure_password_123")


@pytest.fixture
def auth_client(auth_user):
    client = APIClient()
    client.force_authenticate(user=auth_user)
    return client


@pytest.mark.django_db
class TestAuthEndpoints:
    def test_obtain_token_success(self, api_client, auth_user):
        response = api_client.post(
            "/api/token/",
            {"username": "clan_leader", "password": "secure_password_123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_obtain_token_invalid_credentials(self, api_client, auth_user):
        response = api_client.post(
            "/api/token/",
            {"username": "clan_leader", "password": "wrong_password"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client, auth_user):
        token_res = api_client.post(
            "/api/token/",
            {"username": "clan_leader", "password": "secure_password_123"},
            format="json",
        )
        refresh = token_res.data["refresh"]

        response = api_client.post(
            "/api/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data


@pytest.mark.django_db
class TestClanEndpoints:
    def test_clan_permissions(self, api_client, auth_client):
        Clan.objects.create(tag="#2PP", name="Furia Roja")

        # Unauthenticated GET list is allowed (IsAuthenticatedOrReadOnly)
        res_get = api_client.get("/api/clans/")
        assert res_get.status_code == status.HTTP_200_OK
        assert len(res_get.data) == 1

        # Unauthenticated POST is denied
        res_post = api_client.post(
            "/api/clans/",
            {"tag": "#NEW", "name": "New Clan", "medal_threshold": 1600},
            format="json",
        )
        assert res_post.status_code == status.HTTP_401_UNAUTHORIZED

        # Authenticated POST is allowed
        res_post_auth = auth_client.post(
            "/api/clans/",
            {"tag": "#NEW", "name": "New Clan", "medal_threshold": 1600},
            format="json",
        )
        assert res_post_auth.status_code == status.HTTP_201_CREATED
        assert res_post_auth.data["tag"] == "#NEW"

    def test_clan_members_detail(self, auth_client):
        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        Member.objects.create(
            clan=clan, tag="#M1", name="Jugador 1", role="elder", reliability_score=95.0
        )
        Member.objects.create(
            clan=clan, tag="#M2", name="Jugador 2", role="member", reliability_score=80.0
        )
        Member.objects.create(
            clan=clan, tag="#M3", name="Jugador 3", role="member", is_active=False
        )

        # Test both %232PP and 2PP url lookups
        res = auth_client.get("/api/clans/%232PP/members/")
        assert res.status_code == status.HTTP_200_OK
        # Only active members returned
        assert len(res.data) == 2
        assert res.data[0]["tag"] == "#M1"

        res_without_hash = auth_client.get("/api/clans/2PP/members/")
        assert res_without_hash.status_code == status.HTTP_200_OK
        assert len(res_without_hash.data) == 2

    def test_clan_current_war_endpoint(self, auth_client):
        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        Member.objects.create(clan=clan, tag="#M1", name="Jugador 1", role="elder", is_active=True)
        res = auth_client.get("/api/clans/%232PP/current-war/")
        assert res.status_code == status.HTTP_200_OK
        assert "clan" in res.data
        assert "race" in res.data
        assert "stats" in res.data
        assert "clans" in res.data
        assert "participants" in res.data

    @respx.mock
    def test_clan_sync_endpoint(self, auth_client, api_client):
        clan = Clan.objects.create(tag="#2PP", name="Old Name")
        clan_payload = load_fixture("clan_response.json")
        race_payload = load_fixture("currentriverrace_response.json")

        respx.get("https://api.clashroyale.com/v1/clans/%232PP").mock(
            return_value=httpx.Response(200, json=clan_payload)
        )
        respx.get("https://api.clashroyale.com/v1/clans/%232PP/currentriverrace").mock(
            return_value=httpx.Response(200, json=race_payload)
        )

        # Unauthenticated cannot sync
        unauth_res = api_client.post("/api/clans/%232PP/sync/")
        assert unauth_res.status_code == status.HTTP_401_UNAUTHORIZED

        # Authenticated sync
        auth_res = auth_client.post("/api/clans/%232PP/sync/")
        assert auth_res.status_code == status.HTTP_200_OK
        assert auth_res.data["message"] == "Sincronización completada con éxito."

        clan.refresh_from_db()
        assert clan.name == "Furia Roja"
        assert clan.members.count() == 5


@pytest.mark.django_db
class TestWarPassEndpoints:
    def test_war_pass_crud_and_filtering(self, auth_client):
        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        member1 = Member.objects.create(clan=clan, tag="#M1", name="Player 1", role="member")
        Member.objects.create(clan=clan, tag="#M2", name="Player 2", role="elder")

        today = date.today()
        # Create WarPass
        res_create = auth_client.post(
            "/api/war-passes/",
            {
                "member": member1.tag,
                "reason": "Exámenes de la universidad",
                "start_date": str(today),
                "end_date": str(today + timedelta(days=3)),
            },
            format="json",
        )
        assert res_create.status_code == status.HTTP_201_CREATED
        pass_id = res_create.data["id"]

        # Filter by member
        res_filter = auth_client.get(f"/api/war-passes/?member={member1.tag}")
        assert res_filter.status_code == status.HTTP_200_OK
        assert len(res_filter.data) == 1
        assert res_filter.data[0]["id"] == pass_id

        # Filter by clan
        res_clan = auth_client.get(f"/api/war-passes/?clan={clan.tag}")
        assert res_clan.status_code == status.HTTP_200_OK
        assert len(res_clan.data) == 1


@pytest.mark.django_db
class TestRosterActionEndpoints:
    def test_roster_action_execute_and_dismiss(self, auth_client):
        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        member = Member.objects.create(clan=clan, tag="#M1", name="Player 1", role="member")
        action = RosterAction.objects.create(
            clan=clan,
            member=member,
            action_type="kick",
            reason="0/4 ataques en día de guerra",
        )

        # List pending
        res_list = auth_client.get(f"/api/roster-actions/?clan={clan.tag}&status=pending")
        assert res_list.status_code == status.HTTP_200_OK
        assert len(res_list.data) == 1

        # Execute action
        res_exec = auth_client.post(f"/api/roster-actions/{action.id}/execute/")
        assert res_exec.status_code == status.HTTP_200_OK
        assert res_exec.data["action"]["status"] == "executed"
        action.refresh_from_db()
        assert action.status == "executed"
        assert action.executed_at is not None

        # Create another action and dismiss it
        action2 = RosterAction.objects.create(
            clan=clan,
            member=member,
            action_type="demote_member",
            reason="Ataques incompletos",
        )
        res_dismiss = auth_client.post(f"/api/roster-actions/{action2.id}/dismiss/")
        assert res_dismiss.status_code == status.HTTP_200_OK
        assert res_dismiss.data["action"]["status"] == "dismissed"
        action2.refresh_from_db()
        assert action2.status == "dismissed"


@pytest.mark.django_db
class TestMemberEndpoints:
    def test_member_war_history_endpoint(self, auth_client, api_client):
        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        member = Member.objects.create(
            clan=clan,
            tag="#M1",
            name="Super Jugador",
            role="elder",
            reliability_score=100.0,
            trophies=7500,
        )

        race = RiverRace.objects.create(
            clan=clan,
            season_id=120,
            section_index=1,
            state="clans_finished",
        )
        day1 = WarDay.objects.create(
            river_race=race,
            date=date.today() - timedelta(days=1),
            day_index=4,
            day_type="war",
            is_closed=True,
        )
        day2 = WarDay.objects.create(
            river_race=race,
            date=date.today(),
            day_index=5,
            day_type="war",
            is_closed=False,
        )

        WarAttackLog.objects.create(
            war_day=day1,
            member=member,
            attacks_used=4,
            medals_earned=800,
            boat_attacks_count=0,
        )
        WarAttackLog.objects.create(
            war_day=day2,
            member=member,
            attacks_used=2,
            medals_earned=400,
            boat_attacks_count=1,
        )

        # Unauthenticated request is allowed read-only
        res_unauth = api_client.get("/api/members/%23M1/war-history/")
        assert res_unauth.status_code == status.HTTP_200_OK

        # Authenticated with encoded #
        res = auth_client.get("/api/members/%23M1/war-history/")
        assert res.status_code == status.HTTP_200_OK

        # Authenticated without #
        res_no_hash = auth_client.get("/api/members/M1/war-history/")
        assert res_no_hash.status_code == status.HTTP_200_OK

        data = res.data
        assert data["member"]["tag"] == "#M1"
        assert data["member"]["name"] == "Super Jugador"
        assert data["member"]["trophies"] == 7500

        # Summary
        summary = data["summary"]
        assert summary["races_analyzed"] == 1
        assert summary["total_war_days"] == 1
        assert summary["total_attacks_used"] == 4
        assert summary["total_attacks_expected"] == 4
        assert summary["attendance_rate"] == 100.0
        assert summary["total_medals"] == 1200
        assert summary["total_boat_attacks"] == 1

        # Races
        assert len(data["races"]) == 1
        race_data = data["races"][0]
        assert race_data["season_id"] == 120
        assert race_data["section_index"] == 1
        assert race_data["total_attacks"] == 6
        assert len(race_data["days"]) == 2
        assert race_data["days"][0]["attacks_used"] == 4
        assert race_data["days"][1]["attacks_used"] == 2
