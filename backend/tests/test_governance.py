from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.clans.models import Clan, Member, WarPass
from apps.governance.models import RosterAction
from apps.governance.services import GovernanceEngineService
from apps.wars.models import RiverRace, WarAttackLog, WarDay


@pytest.fixture
def test_setup():
    clan = Clan.objects.create(tag="#GOV1", name="Imperio Real", medal_threshold=2000)
    race = RiverRace.objects.create(clan=clan, season_id=10, section_index=1)
    service = GovernanceEngineService()
    return clan, race, service


@pytest.mark.django_db
class TestGovernanceWarDayEvaluation:
    def test_member_missing_attacks_generates_kick(self, test_setup):
        clan, race, service = test_setup
        member = Member.objects.create(tag="#M_KICK", clan=clan, name="Juan", role="member")
        war_day = WarDay.objects.create(
            river_race=race, date=date.today(), day_index=3, day_type="war"
        )

        WarAttackLog.objects.create(war_day=war_day, member=member, attacks_used=2)

        actions = service.evaluate_war_day(war_day)
        assert len(actions) == 1
        assert actions[0].action_type == "kick"
        assert actions[0].member == member
        assert "Expulsión del Clan" in actions[0].reason

        war_day.refresh_from_db()
        assert war_day.is_closed is True

    def test_elder_missing_attacks_generates_demote(self, test_setup):
        clan, race, service = test_setup
        elder = Member.objects.create(tag="#M_ELDER", clan=clan, name="Pedro", role="elder")
        war_day = WarDay.objects.create(
            river_race=race, date=date.today(), day_index=4, day_type="war"
        )

        WarAttackLog.objects.create(war_day=war_day, member=elder, attacks_used=1)

        actions = service.evaluate_war_day(war_day)
        assert len(actions) == 1
        assert actions[0].action_type == "demote_member"
        assert actions[0].member == elder
        assert "Degradación a Miembro" in actions[0].reason

    def test_leadership_sanction_exemption_generates_notice_only(self, test_setup):
        clan, race, service = test_setup
        leader = Member.objects.create(
            tag="#M_LEADER", clan=clan, name="Líder Supremo", role="leader"
        )
        co_leader = Member.objects.create(
            tag="#M_COLEADER", clan=clan, name="Sublíder", role="coLeader"
        )
        war_day = WarDay.objects.create(
            river_race=race, date=date.today(), day_index=5, day_type="war"
        )

        WarAttackLog.objects.create(war_day=war_day, member=leader, attacks_used=0)
        WarAttackLog.objects.create(war_day=war_day, member=co_leader, attacks_used=2)

        actions = service.evaluate_war_day(war_day)
        assert len(actions) == 2
        for action in actions:
            assert action.action_type == "leadership_notice"
            assert "Exento de sanción disciplinaria" in action.reason

    def test_member_with_active_war_pass_is_exempt(self, test_setup):
        clan, race, service = test_setup
        member = Member.objects.create(tag="#M_PASS", clan=clan, name="Estudiante", role="member")
        today = date.today()
        war_day = WarDay.objects.create(river_race=race, date=today, day_index=3, day_type="war")

        WarPass.objects.create(
            member=member,
            reason="Viaje de trabajo",
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
        )

        WarAttackLog.objects.create(war_day=war_day, member=member, attacks_used=0)

        actions = service.evaluate_war_day(war_day)
        assert len(actions) == 0
        assert RosterAction.objects.filter(member=member).count() == 0

    def test_training_day_generates_no_sanctions(self, test_setup):
        clan, race, service = test_setup
        member = Member.objects.create(tag="#M_TRAIN", clan=clan, name="Descanso", role="member")
        training_day = WarDay.objects.create(
            river_race=race, date=date.today(), day_index=1, day_type="training"
        )

        WarAttackLog.objects.create(war_day=training_day, member=member, attacks_used=0)

        actions = service.evaluate_war_day(training_day)
        assert len(actions) == 0
        training_day.refresh_from_db()
        assert training_day.is_closed is True


@pytest.mark.django_db
class TestGovernanceElderPromotions:
    def test_promote_elder_success(self, test_setup):
        clan, race, service = test_setup
        candidate = Member.objects.create(
            tag="#M_CANDIDATE", clan=clan, name="Campeón", role="member"
        )

        today = date.today()
        # 4 días de guerra completando 4 ataques, sumando 3200 medallas y 0 ataques a barco
        for i in range(4):
            day = WarDay.objects.create(
                river_race=race,
                date=today + timedelta(days=i),
                day_index=3 + i,
                day_type="war",
            )
            WarAttackLog.objects.create(
                war_day=day,
                member=candidate,
                attacks_used=4,
                medals_earned=800,
                boat_attacks_count=0,
            )

        promotions = service.evaluate_race_promotions(race)
        assert len(promotions) == 1
        assert promotions[0].action_type == "promote_elder"
        assert promotions[0].member == candidate
        assert "Ascenso a Veterano" in promotions[0].reason

    def test_promote_elder_blocked_by_boat_attacks(self, test_setup):
        clan, race, service = test_setup
        candidate = Member.objects.create(
            tag="#M_BOAT_INFRACTION", clan=clan, name="Traidor", role="member"
        )

        today = date.today()
        for i in range(4):
            day = WarDay.objects.create(
                river_race=race,
                date=today + timedelta(days=i),
                day_index=3 + i,
                day_type="war",
            )
            WarAttackLog.objects.create(
                war_day=day,
                member=candidate,
                attacks_used=4,
                medals_earned=900,
                boat_attacks_count=1 if i == 0 else 0,
            )

        promotions = service.evaluate_race_promotions(race)
        assert len(promotions) == 0

    def test_promote_elder_blocked_by_medals_threshold(self, test_setup):
        clan, race, service = test_setup
        clan.medal_threshold = 2500
        clan.save()

        candidate = Member.objects.create(
            tag="#M_LOW_MEDALS", clan=clan, name="Flojo", role="member"
        )

        today = date.today()
        for i in range(4):
            day = WarDay.objects.create(
                river_race=race,
                date=today + timedelta(days=i),
                day_index=3 + i,
                day_type="war",
            )
            WarAttackLog.objects.create(
                war_day=day,
                member=candidate,
                attacks_used=4,
                medals_earned=500,  # Total 2000 < 2500
                boat_attacks_count=0,
            )

        promotions = service.evaluate_race_promotions(race)
        assert len(promotions) == 0


@pytest.mark.django_db
class TestGovernanceReliabilityScores:
    def test_reliability_score_calculation(self, test_setup):
        clan, race, service = test_setup
        member = Member.objects.create(tag="#M_SCORE", clan=clan, name="Constante", role="member")
        today = date.today()

        # Day 1: 4 ataques (cumplido)
        d1 = WarDay.objects.create(
            river_race=race, date=today - timedelta(days=3), day_index=3, day_type="war"
        )
        WarAttackLog.objects.create(war_day=d1, member=member, attacks_used=4)

        # Day 2: 2 ataques (incompleto)
        d2 = WarDay.objects.create(
            river_race=race, date=today - timedelta(days=2), day_index=4, day_type="war"
        )
        WarAttackLog.objects.create(war_day=d2, member=member, attacks_used=2)

        # Day 3: Pase de guerra aprobado (exento del cálculo)
        d3 = WarDay.objects.create(
            river_race=race, date=today - timedelta(days=1), day_index=5, day_type="war"
        )
        WarPass.objects.create(
            member=member,
            reason="Licencia",
            start_date=today - timedelta(days=1),
            end_date=today - timedelta(days=1),
        )
        WarAttackLog.objects.create(war_day=d3, member=member, attacks_used=0)

        # Day 4: 4 ataques (cumplido)
        d4 = WarDay.objects.create(river_race=race, date=today, day_index=6, day_type="war")
        WarAttackLog.objects.create(war_day=d4, member=member, attacks_used=4)

        # Días esperados: D1, D2, D4 (D3 exento) = 3 días * 4 ataques = 12 ataques esperados
        # Ataques usados: 4 + 2 + 4 = 10 ataques
        # Fiabilidad esperada: (10 / 12) * 100 = 83.33%
        results = service.update_reliability_scores(clan)

        assert results[member.tag] == Decimal("83.33")
        member.refresh_from_db()
        assert member.reliability_score == Decimal("83.33")
