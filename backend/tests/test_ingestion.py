import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

from apps.clans.models import Clan, Member
from apps.ingestion.client import ClashRoyaleClient
from apps.ingestion.exceptions import ClanNotFoundError, RateLimitError
from apps.ingestion.services import SyncClanService, SyncRiverRaceService
from apps.wars.models import WarAttackLog

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> dict:
    return json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))


class TestClashRoyaleClient:
    def test_encode_tag(self):
        assert ClashRoyaleClient.encode_tag("#2PP") == "%232PP"
        assert ClashRoyaleClient.encode_tag("2pp") == "%232PP"
        assert ClashRoyaleClient.encode_tag("#player_tag") == "%23PLAYER_TAG"

    @respx.mock
    def test_client_headers_and_successful_get_clan(self):
        fixture_data = load_fixture("clan_response.json")
        route = respx.get("https://api.clashroyale.com/v1/clans/%232PP").mock(
            return_value=httpx.Response(200, json=fixture_data)
        )

        client = ClashRoyaleClient(api_key="test-secret-key")
        result = client.get_clan("#2PP")

        assert route.called
        assert route.calls.last.request.headers["Authorization"] == "Bearer test-secret-key"
        assert result["name"] == "Furia Roja"
        assert len(result["memberList"]) == 5

    @respx.mock
    def test_client_handles_404_clan_not_found(self):
        respx.get("https://api.clashroyale.com/v1/clans/%23UNKNOWN").mock(
            return_value=httpx.Response(404, json={"reason": "notFound"})
        )

        client = ClashRoyaleClient(api_key="test-key")
        with pytest.raises(ClanNotFoundError):
            client.get_clan("#UNKNOWN")

    @respx.mock
    def test_client_handles_429_rate_limit(self):
        respx.get("https://api.clashroyale.com/v1/clans/%232PP").mock(
            return_value=httpx.Response(429, json={"reason": "rateLimitExceeded"})
        )

        client = ClashRoyaleClient(api_key="test-key", max_retries=2, retry_delay=0.01)
        with pytest.raises(RateLimitError):
            client.get_clan("#2PP")


@pytest.mark.django_db
class TestSyncServices:
    @respx.mock
    def test_sync_clan_service(self):
        clan_data = load_fixture("clan_response.json")
        respx.get("https://api.clashroyale.com/v1/clans/%232PP").mock(
            return_value=httpx.Response(200, json=clan_data)
        )

        clan = Clan.objects.create(tag="#2PP", name="Nombre Antiguo")
        # Miembro que ya no estará en la lista (deberá desactivarse)
        Member.objects.create(tag="#P_OLD", clan=clan, name="Ex Miembro", is_active=True)

        service = SyncClanService()
        synced_clan = service.sync(clan)

        assert synced_clan.name == "Furia Roja"
        assert Member.objects.filter(clan=clan).count() == 6

        # 5 activos provenientes de la API
        assert Member.objects.filter(clan=clan, is_active=True).count() == 5
        # El antiguo miembro fue desactivado
        assert Member.objects.get(tag="#P_OLD").is_active is False

        leader = Member.objects.get(tag="#P1")
        assert leader.name == "Carlos L"
        assert leader.role == "leader"

        elder = Member.objects.get(tag="#P3")
        assert elder.name == "Marcos Vet"
        assert elder.role == "elder"

    @respx.mock
    def test_sync_river_race_service(self):
        race_data = load_fixture("currentriverrace_response.json")
        respx.get("https://api.clashroyale.com/v1/clans/%232PP/currentriverrace").mock(
            return_value=httpx.Response(200, json=race_data)
        )

        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        service = SyncRiverRaceService()
        target_date = date(2026, 9, 30)

        river_race, war_day = service.sync(clan, target_date=target_date)

        assert river_race.section_index == 1
        assert river_race.state == "fullState"

        # periodIndex 3 significa jornada de guerra (day_index=3, day_type="war")
        assert war_day.day_index == 3
        assert war_day.day_type == "war"
        assert war_day.date == target_date

        logs = WarAttackLog.objects.filter(war_day=war_day)
        assert logs.count() == 5

        # Carlos usó 4 ataques y obtuvo 3600 medallas
        log_p1 = logs.get(member__tag="#P1")
        assert log_p1.attacks_used == 4
        assert log_p1.medals_earned == 3600
        assert log_p1.boat_attacks_count == 0

        # Marcos usó 4 ataques pero cometió 1 ataque a barco
        log_p3 = logs.get(member__tag="#P3")
        assert log_p3.attacks_used == 4
        assert log_p3.boat_attacks_count == 1

        # Lucas usó 2 ataques
        log_p4 = logs.get(member__tag="#P4")
        assert log_p4.attacks_used == 2
        assert log_p4.medals_earned == 1400
