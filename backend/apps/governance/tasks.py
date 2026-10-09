import logging

from celery import shared_task

from apps.clans.models import Clan
from apps.notifications.dispatcher import NotificationDispatcher
from apps.wars.models import WarDay

from .services import GovernanceEngineService

logger = logging.getLogger(__name__)


@shared_task(name="apps.governance.tasks.task_evaluate_war_day_governance")
def task_evaluate_war_day_governance(clan_tag: str | None = None) -> int:
    """Evaluate closed war days, generate sanctions, and dispatch reports."""
    clans = (
        Clan.objects.filter(tag=clan_tag, is_active=True)
        if clan_tag
        else Clan.objects.filter(is_active=True)
    )
    engine = GovernanceEngineService()
    dispatcher = NotificationDispatcher()
    total_actions_generated = 0

    for clan in clans:
        effective_today = clan.get_current_war_date()
        open_war_days = WarDay.objects.filter(
            river_race__clan=clan,
            day_type="war",
            is_closed=False,
            date__lt=effective_today,
        ).order_by("date")

        for war_day in open_war_days:
            try:
                actions = engine.evaluate_war_day(war_day)
                total_actions_generated += len(actions)

                # Dispatch daily roster report to configured notification channels
                if actions:
                    dispatcher.dispatch_roster_report(clan, actions, war_day.date)

                    notices = [a for a in actions if a.action_type == "leadership_notice"]
                    if notices:
                        dispatcher.dispatch_leadership_notices(clan, notices)

                # Check if river race has concluded to evaluate elder promotions
                race = war_day.river_race
                remaining_open_days = race.war_days.filter(day_type="war", is_closed=False).count()
                if remaining_open_days == 0:
                    promotions = engine.evaluate_race_promotions(race)
                    if promotions:
                        total_actions_generated += len(promotions)
                        dispatcher.dispatch_roster_report(clan, promotions, war_day.date)

                # Update historical attendance scores
                engine.update_reliability_scores(clan)

            except Exception as exc:
                logger.exception(
                    f"Error evaluating governance for clan {clan.tag} on {war_day.date}: {exc}"
                )

    return total_actions_generated
