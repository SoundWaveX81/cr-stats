import logging
from datetime import date, datetime, time
from datetime import timezone as dt_timezone

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
def task_send_pending_attack_reminders(
    clan_tag: str | None = None, force: bool = False
) -> dict[str, int]:
    """Send reminder alerts to active clan members who have pending war attacks before 10:00 UTC."""
    clans = (
        Clan.objects.filter(tag=clan_tag, is_active=True)
        if clan_tag
        else Clan.objects.filter(is_active=True)
    )
    today = date.today()
    dispatcher = NotificationDispatcher()
    sync_race_service = SyncRiverRaceService()
    summary = {}

    now_utc = datetime.now(dt_timezone.utc)
    today_reset = datetime.combine(now_utc.date(), time(10, 0), tzinfo=dt_timezone.utc)
    if now_utc >= today_reset:
        hours_left = 0
    else:
        hours_left = max(0, int((today_reset - now_utc).total_seconds() // 3600))

    for clan in clans:
        # Sync live war data from Clash Royale API to prevent false reminders
        try:
            sync_race_service.sync(clan)
        except Exception as exc:
            logger.warning(f"Could not live sync clan {clan.tag} before reminders: {exc}")

        # Find today's open war day
        open_war_day = WarDay.objects.filter(
            river_race__clan=clan,
            day_type="war",
            is_closed=False,
            date=today,
        ).first()

        if not open_war_day and force:
            open_war_day = (
                WarDay.objects.filter(river_race__clan=clan, day_type="war")
                .order_by("-date")
                .first()
            )

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
                        reliability_score=float(member.reliability_score),
                    )
                )

        if pending_items:
            dispatcher.dispatch_pending_attacks(
                clan, pending_items, open_war_day.date, hours_left=hours_left
            )
            summary[clan.tag] = len(pending_items)
        else:
            # If 0 pending: send congratulatory alert at day close (10:00 UTC), silence during intermediate hours
            if force or hours_left == 0 or now_utc.hour == 10:
                dispatcher.dispatch_all_attacks_completed(clan, open_war_day.date)
            else:
                logger.info(
                    f"All members of clan {clan.name} completed attacks. Silencing reminder ({hours_left}h left)."
                )
            summary[clan.tag] = 0

    return summary
