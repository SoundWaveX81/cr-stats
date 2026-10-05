from datetime import date, timedelta

import pytest
from django.contrib import admin
from django.db import IntegrityError

from apps.clans.models import Clan, Member, WarPass
from apps.governance.models import RosterAction
from apps.notifications.models import NotificationChannel
from apps.wars.models import RiverRace, WarAttackLog, WarDay


@pytest.mark.django_db
class TestClanAndMemberModels:
    def test_clan_creation_and_tag_normalization(self):
        clan = Clan.objects.create(tag="2pp", name="Los Titanes")
        assert clan.tag == "#2PP"
        assert clan.medal_threshold == 2000
        assert clan.is_active is True
        assert str(clan) == "Los Titanes (#2PP)"

    def test_member_creation_and_cascade(self):
        clan = Clan.objects.create(tag="#CLAN1", name="Alpha")
        member = Member.objects.create(
            tag="player123",
            clan=clan,
            name="Rey Bárbaro",
            role="elder",
        )
        assert member.tag == "#PLAYER123"
        assert member.role == "elder"
        assert float(member.reliability_score) == 100.00
        assert "Rey Bárbaro (#PLAYER123)" in str(member)

        # Cascade test
        clan.delete()
        assert Member.objects.filter(tag="#PLAYER123").count() == 0

    def test_war_pass_activity_window(self):
        clan = Clan.objects.create(tag="#CLAN2", name="Beta")
        member = Member.objects.create(tag="#M1", clan=clan, name="Arquera")
        today = date.today()
        war_pass = WarPass.objects.create(
            member=member,
            reason="Exámenes universitarios",
            start_date=today - timedelta(days=2),
            end_date=today + timedelta(days=2),
        )

        assert war_pass.is_active_on(today) is True
        assert war_pass.is_active_on(today - timedelta(days=3)) is False
        assert war_pass.is_active_on(today + timedelta(days=3)) is False
        assert "Arquera" in str(war_pass)


@pytest.mark.django_db
class TestWarModels:
    def test_river_race_and_unique_constraint(self):
        clan = Clan.objects.create(tag="#RACECLAN", name="Marineros")
        standings_data = [
            {"rank": 1, "tag": "#RIVAL", "name": "Rival Clan", "fame": 12000},
            {"rank": 2, "tag": "#RACECLAN", "name": "Corredores", "fame": 10000},
        ]
        race = RiverRace.objects.create(
            clan=clan,
            season_id=55,
            section_index=1,
            clan_score=10000,
            standings=standings_data,
        )
        assert "Carrera T55-S1" in str(race)

        standings_objs = race.get_standings_objects()
        assert len(standings_objs) == 2
        assert standings_objs[0].rank == 1
        assert standings_objs[0].diff == 2000
        assert standings_objs[0].is_target is False
        assert standings_objs[1].rank == 2
        assert standings_objs[1].diff == 0
        assert standings_objs[1].is_target is True

        with pytest.raises(IntegrityError):
            RiverRace.objects.create(
                clan=clan,
                season_id=55,
                section_index=1,
            )

    def test_war_day_and_unique_constraint(self):
        clan = Clan.objects.create(tag="#DAYCLAN", name="Guerreros")
        race = RiverRace.objects.create(clan=clan, season_id=55, section_index=2)
        today = date.today()
        war_day = WarDay.objects.create(
            river_race=race,
            date=today,
            day_index=3,
            day_type="war",
        )
        assert war_day.day_type == "war"
        assert war_day.is_closed is False
        assert "Guerra D3" in str(war_day)

        with pytest.raises(IntegrityError):
            WarDay.objects.create(
                river_race=race,
                date=today,
                day_index=4,
            )

    def test_war_attack_log_and_unique_constraint(self):
        clan = Clan.objects.create(tag="#ATTACKCLAN", name="Gladiadores")
        member = Member.objects.create(tag="#P99", clan=clan, name="Pekka")
        race = RiverRace.objects.create(clan=clan, season_id=55, section_index=3)
        war_day = WarDay.objects.create(
            river_race=race, date=date.today(), day_index=3, day_type="war"
        )

        log = WarAttackLog.objects.create(
            war_day=war_day,
            member=member,
            attacks_used=4,
            medals_earned=3600,
            boat_attacks_count=0,
        )
        assert log.attacks_used == 4
        assert "Pekka: 4/4" in str(log)

        with pytest.raises(IntegrityError):
            WarAttackLog.objects.create(
                war_day=war_day,
                member=member,
                attacks_used=2,
            )


@pytest.mark.django_db
class TestGovernanceAndNotificationModels:
    def test_roster_action_lifecycle(self):
        clan = Clan.objects.create(tag="#GOVCLAN", name="Conquistadores")
        member = Member.objects.create(tag="#P_SANCTION", clan=clan, name="Inactivo")
        action = RosterAction.objects.create(
            clan=clan,
            member=member,
            action_type="demote_member",
            reason="Faltaron 2 ataques en Día de Guerra",
        )
        assert action.status == "pending"
        assert action.executed_at is None
        assert "Degradación a Miembro" in str(action)

        action.mark_executed()
        assert action.status == "executed"
        assert action.executed_at is not None

        action2 = RosterAction.objects.create(
            clan=clan,
            member=member,
            action_type="kick",
            reason="Prueba descarte",
        )
        action2.mark_dismissed()
        assert action2.status == "dismissed"

    def test_notification_channel_configuration(self):
        clan = Clan.objects.create(tag="#NOTIFCLAN", name="Comunicadores")
        channel = NotificationChannel.objects.create(
            clan=clan,
            provider="discord_webhook",
            config={"webhook_url": "https://discord.com/api/webhooks/123/xyz"},
        )
        assert channel.provider == "discord_webhook"
        assert channel.is_active is True
        assert "Discord Webhook" in str(channel)


def test_models_registered_in_django_admin():
    """Verify that all core domain models are registered in Django Admin."""
    expected_models = [
        Clan,
        Member,
        WarPass,
        RiverRace,
        WarDay,
        WarAttackLog,
        RosterAction,
        NotificationChannel,
    ]
    registered_models = list(admin.site._registry.keys())
    for model in expected_models:
        assert model in registered_models, f"{model.__name__} no está registrado en admin.site"
