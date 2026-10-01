import logging
from datetime import date

from apps.clans.models import Clan
from apps.governance.models import RosterAction

from .base import BaseNotificationAdapter, PendingAttackItem

logger = logging.getLogger(__name__)


class ConsoleNotificationAdapter(BaseNotificationAdapter):
    """Logs notification events to system logger / stdout."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    def send_pending_attacks_alert(
        self, clan: Clan, pending_items: list[PendingAttackItem], war_day_date: date
    ) -> bool:
        lines = [f"[ALERTA ATAQUES PENDIENTES] {clan.name} ({war_day_date}):"]
        for item in pending_items:
            lines.append(
                f" - {item.member_name} ({item.member_tag}, {item.role}): "
                f"{item.attacks_used}/4 usados ({item.remaining_attacks} restantes)"
            )
        msg = "\n".join(lines)
        logger.info(msg)
        return True

    def send_daily_roster_report(
        self, clan: Clan, actions: list[RosterAction], war_day_date: date
    ) -> bool:
        lines = [f"[REPORTE DE GOBERNANZA] {clan.name} ({war_day_date}):"]
        if not actions:
            lines.append(" - Sin sanciones ni ascensos hoy. ¡100% cumplimiento!")
        else:
            for act in actions:
                lines.append(
                    f" - [{act.get_action_type_display()}] {act.member.name}: {act.reason}"
                )
        msg = "\n".join(lines)
        logger.info(msg)
        return True

    def send_leadership_notice(self, clan: Clan, notices: list[RosterAction]) -> bool:
        lines = [f"[AVISO A LIDERAZGO] {clan.name}:"]
        for notice in notices:
            lines.append(
                f" - {notice.member.name} ({notice.member.get_role_display()}): {notice.reason}"
            )
        msg = "\n".join(lines)
        logger.info(msg)
        return True
