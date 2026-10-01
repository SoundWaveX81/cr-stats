from decimal import Decimal

from django.db import transaction

from apps.clans.models import Clan
from apps.governance.models import RosterAction
from apps.wars.models import RiverRace, WarAttackLog, WarDay


class GovernanceEngineService:
    """Core domain service for clan war governance, sanctions, and promotion rules."""

    REQUIRED_WAR_ATTACKS = 4

    @transaction.atomic
    def evaluate_war_day(self, war_day: WarDay) -> list[RosterAction]:
        """Evaluate attendance and attack completion at the close of a War Day.

        Training days are excluded from sanctions.
        """
        if war_day.day_type != "war":
            war_day.is_closed = True
            war_day.save(update_fields=["is_closed", "updated_at"])
            return []

        clan = war_day.river_race.clan
        actions_generated = []
        active_members = clan.members.filter(is_active=True)

        attack_logs = {log.member_id: log for log in WarAttackLog.objects.filter(war_day=war_day)}

        for member in active_members:
            log = attack_logs.get(member.tag)
            attacks_used = log.attacks_used if log else 0

            if attacks_used < self.REQUIRED_WAR_ATTACKS:
                # Check for an active, approved WarPass on this date
                has_pass = member.war_passes.filter(
                    start_date__lte=war_day.date,
                    end_date__gte=war_day.date,
                ).exists()

                if has_pass:
                    continue

                if member.role in ("leader", "coLeader"):
                    action_type = "leadership_notice"
                    reason = (
                        f"Liderazgo: {attacks_used}/4 ataques en {war_day.date}. "
                        "Exento de sanción disciplinaria según ADR 0002."
                    )
                elif member.role == "elder":
                    action_type = "demote_member"
                    reason = (
                        f"Degradación a Miembro: Solo {attacks_used}/4 ataques "
                        f"completados en jornada de guerra ({war_day.date})."
                    )
                else:
                    action_type = "kick"
                    reason = (
                        f"Expulsión del Clan: Solo {attacks_used}/4 ataques "
                        f"completados en jornada de guerra ({war_day.date})."
                    )

                action, created = RosterAction.objects.get_or_create(
                    clan=clan,
                    member=member,
                    war_day=war_day,
                    action_type=action_type,
                    status="pending",
                    defaults={"reason": reason},
                )
                if created:
                    actions_generated.append(action)

        war_day.is_closed = True
        war_day.save(update_fields=["is_closed", "updated_at"])
        return actions_generated

    @transaction.atomic
    def evaluate_race_promotions(self, river_race: RiverRace) -> list[RosterAction]:
        """Evaluate active members for automatic elder promotion at race completion."""
        war_days = river_race.war_days.filter(day_type="war")
        if not war_days.exists():
            return []

        num_war_days = war_days.count()
        expected_attacks = num_war_days * self.REQUIRED_WAR_ATTACKS
        medal_threshold = river_race.clan.medal_threshold
        candidate_members = river_race.clan.members.filter(is_active=True, role="member")

        promotions = []
        for member in candidate_members:
            logs = WarAttackLog.objects.filter(war_day__in=war_days, member=member)

            if logs.count() < num_war_days:
                continue

            total_attacks = sum(log.attacks_used for log in logs)
            if total_attacks < expected_attacks:
                continue

            total_medals = sum(log.medals_earned for log in logs)
            if total_medals < medal_threshold:
                continue

            total_boat_attacks = sum(log.boat_attacks_count for log in logs)
            if total_boat_attacks > 0:
                continue

            reason = (
                f"Ascenso a Veterano: 100% de ataques completados ({total_attacks}/{expected_attacks}), "
                f"{total_medals} medallas acumuladas (umbral: {medal_threshold}) y 0 ataques a barcos."
            )
            action, created = RosterAction.objects.get_or_create(
                clan=river_race.clan,
                member=member,
                action_type="promote_elder",
                status="pending",
                defaults={"reason": reason},
            )
            if created:
                promotions.append(action)

        return promotions

    @transaction.atomic
    def update_reliability_scores(self, clan: Clan, lookback_days: int = 14) -> dict[str, Decimal]:
        """Recalculate attendance reliability scores over the latest war days."""
        war_days = list(
            WarDay.objects.filter(
                river_race__clan=clan,
                day_type="war",
                is_closed=True,
            ).order_by("-date")[:lookback_days]
        )
        if not war_days:
            return {}

        results = {}
        for member in clan.members.filter(is_active=True):
            expected_attacks = 0
            actual_attacks = 0

            for day in war_days:
                has_pass = member.war_passes.filter(
                    start_date__lte=day.date,
                    end_date__gte=day.date,
                ).exists()

                if has_pass:
                    continue

                expected_attacks += self.REQUIRED_WAR_ATTACKS
                log = WarAttackLog.objects.filter(war_day=day, member=member).first()
                if log:
                    actual_attacks += min(log.attacks_used, self.REQUIRED_WAR_ATTACKS)

            if expected_attacks == 0:
                score = Decimal("100.00")
            else:
                score = round(
                    Decimal(actual_attacks) / Decimal(expected_attacks) * Decimal("100.00"), 2
                )

            member.reliability_score = score
            member.save(update_fields=["reliability_score", "updated_at"])
            results[member.tag] = score

        return results
