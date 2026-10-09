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
from apps.wars.models import RiverRace, WarAttackLog, WarDay

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

        # Now simulate Day 4 sync where cumulative fame increases for Carlos from 3600 to 4500
        race_data_day4 = dict(race_data)
        race_data_day4["periodIndex"] = 4  # Day 4 (Friday)
        race_data_day4["clan"] = dict(race_data["clan"])
        race_data_day4["clan"]["participants"] = [
            dict(p) for p in race_data["clan"]["participants"]
        ]
        p1 = next(p for p in race_data_day4["clan"]["participants"] if p["tag"] == "#P1")
        p1["fame"] = 4500
        p1["decksUsedToday"] = 4
        p1["boatAttacks"] = 2  # was 0, now 2

        respx.get("https://api.clashroyale.com/v1/clans/%232PP/currentriverrace").mock(
            return_value=httpx.Response(200, json=race_data_day4)
        )
        _, war_day_4 = service.sync(clan, target_date=date(2026, 10, 1))
        log_p1_d4 = WarAttackLog.objects.get(war_day=war_day_4, member__tag="#P1")
        # Incremental medals for Day 4 should be 4500 - 3600 = 900
        assert log_p1_d4.medals_earned == 900
        # Incremental boat attacks should be 2 - 0 = 2
        assert log_p1_d4.boat_attacks_count == 2

    @respx.mock
    def test_sync_race_history(self):
        from decimal import Decimal

        log_data = {
            "items": [
                {
                    "seasonId": 136,
                    "sectionIndex": 2,
                    "createdDate": "20260928T093605.000Z",
                    "standings": [
                        {
                            "clan": {
                                "tag": "#2PP",
                                "name": "Furia Roja",
                                "fame": 10000,
                                "participants": [
                                    {
                                        "tag": "#P1",
                                        "name": "Carlos",
                                        "decksUsed": 16,
                                        "fame": 3600,
                                        "boatAttacks": 0,
                                    },
                                    {
                                        "tag": "#P2",
                                        "name": "David",
                                        "decksUsed": 8,
                                        "fame": 1800,
                                        "boatAttacks": 0,
                                    },
                                ],
                            }
                        }
                    ],
                }
            ]
        }
        respx.get("https://api.clashroyale.com/v1/clans/%232PP/riverracelog").mock(
            return_value=httpx.Response(200, json=log_data)
        )

        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")
        Member.objects.create(tag="#P1", clan=clan, name="Carlos", is_active=True)
        Member.objects.create(tag="#P2", clan=clan, name="David", is_active=True)

        service = SyncRiverRaceService()
        synced = service.sync_race_history(clan)

        assert synced == 1
        race = RiverRace.objects.get(clan=clan, season_id=136, section_index=2)
        assert race.state == "clans_finished"
        assert race.war_days.count() == 4

        p1 = Member.objects.get(tag="#P1")
        p2 = Member.objects.get(tag="#P2")
        assert p1.reliability_score == Decimal("100.00")
        assert p2.reliability_score == Decimal("50.00")

    @respx.mock
    def test_sync_river_race_season_transition(self):
        clan = Clan.objects.create(tag="#2PP", name="Furia Roja")

        # Ongoing race from season 136, week 3
        old_race = RiverRace.objects.create(
            clan=clan,
            season_id=136,
            section_index=3,
            state="matched",
            clan_score=10000,
        )
        old_day = WarDay.objects.create(
            river_race=old_race,
            day_index=6,
            date=date(2026, 10, 4),
            day_type="war",
            is_closed=False,
        )

        # API now returns sectionIndex=0 (rollover to next season)
        race_data = {
            "sectionIndex": 0,
            "periodIndex": 0,
            "state": "full",
            "clan": {
                "tag": "#2PP",
                "name": "Furia Roja",
                "fame": 0,
                "participants": [],
            },
            "clans": [],
        }
        respx.get("https://api.clashroyale.com/v1/clans/%232PP/currentriverrace").mock(
            return_value=httpx.Response(200, json=race_data)
        )

        service = SyncRiverRaceService()
        target_date = date(2026, 10, 5)
        new_race, new_war_day = service.sync(clan, target_date=target_date)

        # Previous race should be closed
        old_race.refresh_from_db()
        old_day.refresh_from_db()
        assert old_race.state == "clans_finished"
        assert old_day.is_closed is True

        # New race should advance to season 137, section 0
        assert new_race.season_id == 137
        assert new_race.section_index == 0
        assert new_race.state == "full"
        assert new_war_day.day_index == 0
        assert new_war_day.day_type == "training"
