import logging
from datetime import date

from celery import shared_task

from apps.clans.models import Clan
from apps.notifications.adapters import PendingAttackItem
from apps.notifications.dispatcher import NotificationDispatcher
from apps.wars.models import WarAttackLog, WarDay

from .services import SyncClanService, SyncRiverRaceService

logger = logging.getLogger(__name__)


@shared_task(name="apps.ingestion.tasks.task_sync_clan_data")
def task_sync_clan_data(clan_tag: str | None = None) -> int:
    """Sync clan roster and current river race for one or all active clans."""
    clans = (
        Clan.objects.filter(tag=clan_tag, is_active=True)
        if clan_tag
        else Clan.objects.filter(is_active=True)
    )
    synced_count = 0
    sync_clan_service = SyncClanService()
    sync_race_service = SyncRiverRaceService()

    for clan in clans:
        try:
            sync_clan_service.sync(clan)
            sync_race_service.sync(clan)
            synced_count += 1
            logger.info(f"Successfully synced clan {clan.name} ({clan.tag})")
        except Exception as exc:
            logger.exception(f"Error syncing clan {clan.tag}: {exc}")

    return synced_count


@shared_task(name="apps.ingestion.tasks.task_sync_river_race_history")
def task_sync_river_race_history(clan_tag: str | None = None) -> int:
    """Sync completed past river races log (/riverracelog) for active clans."""
    clans = (
        Clan.objects.filter(tag=clan_tag, is_active=True)
        if clan_tag
        else Clan.objects.filter(is_active=True)
    )
    total_races = 0
    sync_race_service = SyncRiverRaceService()

    for clan in clans:
        try:
            races = sync_race_service.sync_race_history(clan)
            total_races += races
            logger.info(f"Successfully ingested {races} past races for {clan.name} ({clan.tag})")
        except Exception as exc:
            logger.exception(f"Error ingesting race history for {clan.tag}: {exc}")

    return total_races


@shared_task(name="apps.ingestion.tasks.task_send_pending_attack_reminders")
def task_send_pending_attack_reminders(clan_tag: str | None = None) -> dict[str, int]:
    """Send reminder alerts to active clan members who have pending war attacks."""
    clans = (
        Clan.objects.filter(tag=clan_tag, is_active=True)
        if clan_tag
        else Clan.objects.filter(is_active=True)
    )
    today = date.today()
    dispatcher = NotificationDispatcher()
    summary = {}

    for clan in clans:
        # Find today's open war day
        open_war_day = WarDay.objects.filter(
            river_race__clan=clan,
            day_type="war",
            is_closed=False,
            date=today,
        ).first()

        if not open_war_day:
            continue

        active_members = clan.members.filter(is_active=True)
        attack_logs = {
            log.member_id: log for log in WarAttackLog.objects.filter(war_day=open_war_day)
        }

        pending_items = []
        for member in active_members:
            # Skip if member has an approved WarPass
            has_pass = member.war_passes.filter(
                start_date__lte=open_war_day.date,
                end_date__gte=open_war_day.date,
            ).exists()
            if has_pass:
                continue

            log = attack_logs.get(member.tag)
            used = log.attacks_used if log else 0
            if used < 4:
                pending_items.append(
                    PendingAttackItem(
                        member_tag=member.tag,
                        member_name=member.name,
                        role=member.role,
                        attacks_used=used,
                        remaining_attacks=4 - used,
                    )
                )

        if pending_items:
            dispatcher.dispatch_pending_attacks(clan, pending_items, open_war_day.date)
            summary[clan.tag] = len(pending_items)

    return summary
