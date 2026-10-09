from unittest.mock import MagicMock

import pytest

from apps.clans.models import Clan
from apps.wars.helpers import extract_clan_fame
from apps.wars.models import RiverRace
from apps.wars.services import CurrentWarService


def test_extract_clan_fame_various_payloads():
    # 1. Live war day payload: fame is 0, periodPoints > 0, participants present
    live_clan = {
        "tag": "#CLAN1",
        "name": "Live Clan",
        "fame": 0,
        "periodPoints": 29150,
        "participants": [
            {"tag": "#P1", "fame": 1400},
            {"tag": "#P2", "fame": 27750},
        ],
    }
    assert extract_clan_fame(live_clan) == 29150

    # 2. Live rival clan without participants list but with periodPoints
    rival_without_p = {
        "tag": "#RIVAL",
        "fame": 0,
        "periodPoints": 27350,
    }
    assert extract_clan_fame(rival_without_p) == 27350

    # 3. Concluded race from history: fame > 0, periodPoints 0
    concluded_clan = {
        "tag": "#OLD",
        "fame": 124900,
        "periodPoints": 0,
        "participants": [{"fame": 124900}],
    }
    assert extract_clan_fame(concluded_clan) == 124900

    # 4. Standard fixture format with fame only
    fixture_clan = {
        "tag": "#FIX",
        "fame": 11000,
    }
    assert extract_clan_fame(fixture_clan) == 11000

    # 5. Empty or None
    assert extract_clan_fame(None) == 0
    assert extract_clan_fame({}) == 0


@pytest.mark.django_db
def test_current_war_service_build_from_live_and_diffs():
    clan = Clan.objects.create(tag="#P8CCG2UJ", name="Colombia")
    service = CurrentWarService(client=MagicMock())

    api_payload = {
        "state": "full",
        "sectionIndex": 0,
        "periodIndex": 3,
        "periodType": "warDay",
        "clan": {
            "tag": "#P8CCG2UJ",
            "name": "Colombia",
            "fame": 0,
            "periodPoints": 29150,
            "clanScore": 3950,
            "participants": [{"tag": "#P1", "fame": 29150}],
        },
        "clans": [
            {
                "tag": "#P8CCG2UJ",
                "name": "Colombia",
                "fame": 0,
                "periodPoints": 29150,
                "clanScore": 3950,
                "participants": [{"tag": "#P1", "fame": 29150}],
            },
            {
                "tag": "#PRYQ8PRC",
                "name": "Absolute_LegenS",
                "fame": 0,
                "periodPoints": 29100,
                "clanScore": 3913,
                "participants": [{"tag": "#P2", "fame": 29100}],
            },
            {
                "tag": "#8PCC8Q2C",
                "name": "Penguin Soldier",
                "fame": 0,
                "periodPoints": 8100,
                "clanScore": 4053,
                "participants": [{"tag": "#P3", "fame": 8100}],
            },
        ],
    }

    overview = service._build_from_live(clan, api_payload, {}, {})

    # Colombia should be #1 with 29150 medals, not #3
    assert overview["clan"]["position"] == 1
    assert overview["clan"]["fame"] == 29150
    assert overview["stats"]["first_place_fame"] == 29150
    assert overview["stats"]["gap_to_first"] == 0

    clans = overview["clans"]
    assert len(clans) == 3

    colombia = clans[0]
    assert colombia["name"] == "Colombia"
    assert colombia["rank"] == 1
    assert colombia["fame"] == 29150
    assert colombia["diff"] == 0

    second = clans[1]
    assert second["name"] == "Absolute_LegenS"
    assert second["rank"] == 2
    assert second["fame"] == 29100
    assert second["diff"] == -50

    third = clans[2]
    assert third["name"] == "Penguin Soldier"
    assert third["rank"] == 3
    assert third["fame"] == 8100
    assert third["diff"] == -21050


@pytest.mark.django_db
def test_river_race_standings_diff_and_order():
    clan = Clan.objects.create(tag="#MYCLAN", name="My Clan")
    standings_data = [
        {"rank": 1, "tag": "#MYCLAN", "name": "My Clan", "fame": 25000, "clan_score": 4000},
        {"rank": 2, "tag": "#RIVAL_TIED", "name": "Tied Rival", "fame": 25000, "clan_score": 3900},
        {
            "rank": 3,
            "tag": "#RIVAL_LOWER",
            "name": "Lower Rival",
            "fame": 20000,
            "clan_score": 3800,
        },
    ]
    race = RiverRace.objects.create(
        clan=clan,
        season_id=10,
        section_index=1,
        clan_score=25000,
        standings=standings_data,
    )

    objs = race.get_standings_objects()
    assert len(objs) == 3
    assert objs[0].is_target is True
    assert objs[0].diff == 0

    assert objs[1].is_target is False
    assert objs[1].diff == 0

    assert objs[2].is_target is False
    assert objs[2].diff == -5000
