import logging
from datetime import date

import httpx

from apps.clans.models import Clan
from apps.governance.models import RosterAction

from .base import BaseNotificationAdapter, PendingAttackItem

logger = logging.getLogger(__name__)

COLOR_RED = 15158332  # 0xE74C3C - Kick
COLOR_ORANGE = 15105570  # 0xE67E22 - Demote / Notice
COLOR_GREEN = 3066993  # 0x2ECC71 - Promote
COLOR_YELLOW = 15844367  # 0xF1C40F - Pending reminder
COLOR_BLUE = 3447003  # 0x3498DB - Info / Clean


class DiscordWebhookNotificationAdapter(BaseNotificationAdapter):
    """Sends rich Discord embeds via Incoming Webhooks."""

    def __init__(self, config: dict | None = None, timeout: float = 10.0):
        self.config = config or {}
        self.webhook_url = self.config.get("webhook_url", "")
        self.timeout = timeout

    def _send_payload(self, payload: dict) -> bool:
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured.")
            return False

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.webhook_url, json=payload)
                if resp.status_code in (200, 204):
                    return True
                logger.error(f"Discord webhook failed with HTTP {resp.status_code}: {resp.text}")
                return False
        except httpx.HTTPError as exc:
            logger.error(f"Network error sending Discord webhook: {exc}")
            return False

    def send_pending_attacks_alert(
        self, clan: Clan, pending_items: list[PendingAttackItem], war_day_date: date
    ) -> bool:
        if not pending_items:
            return True

        fields = []
        for item in pending_items[:25]:  # Discord limit: max 25 fields
            fields.append(
                {
                    "name": f"{item.member_name} ({item.role})",
                    "value": f"Ataques realizados: **{item.attacks_used}/4** (Faltan {item.remaining_attacks})",
                    "inline": True,
                }
            )

        embed = {
            "title": f"⚠️ Recordatorio: Ataques Pendientes - {clan.name}",
            "description": f"Jornada del **{war_day_date}**. ¡Quedan pocas horas antes del reinicio a las 10:00 UTC!",
            "color": COLOR_YELLOW,
            "fields": fields,
            "footer": {"text": "Clan War Governance System"},
        }
        return self._send_payload({"embeds": [embed]})

    def send_daily_roster_report(
        self, clan: Clan, actions: list[RosterAction], war_day_date: date
    ) -> bool:
        if not actions:
            embed = {
                "title": f"🛡️ Reporte Diario de Guerra - {clan.name}",
                "description": f"Jornada del **{war_day_date}**: ¡Todos los miembros completaron sus ataques! 100% de asistencia.",
                "color": COLOR_GREEN,
                "footer": {"text": "Clan War Governance System"},
            }
            return self._send_payload({"embeds": [embed]})

        action_types = {act.action_type for act in actions}
        if "kick" in action_types:
            color = COLOR_RED
        elif "demote_member" in action_types or "leadership_notice" in action_types:
            color = COLOR_ORANGE
        else:
            color = COLOR_GREEN

        fields = []
        for act in actions[:25]:
            fields.append(
                {
                    "name": f"[{act.get_action_type_display()}] {act.member.name}",
                    "value": act.reason,
                    "inline": False,
                }
            )

        embed = {
            "title": f"⚖️ Reporte de Gobernanza - {clan.name}",
            "description": f"Evaluación de la jornada **{war_day_date}**. Acciones generadas pendientes de confirmar en el juego:",
            "color": color,
            "fields": fields,
            "footer": {"text": "Clan War Governance System"},
        }
        return self._send_payload({"embeds": [embed]})

    def send_leadership_notice(self, clan: Clan, notices: list[RosterAction]) -> bool:
        if not notices:
            return True

        fields = []
        for notice in notices[:25]:
            fields.append(
                {
                    "name": f"{notice.member.name} ({notice.member.get_role_display()})",
                    "value": notice.reason,
                    "inline": False,
                }
            )

        embed = {
            "title": f"👑 Aviso de Cumplimiento a Líderes - {clan.name}",
            "description": "Información de auditoría sobre miembros del equipo de liderazgo con faltas de ataques:",
            "color": COLOR_ORANGE,
            "fields": fields,
            "footer": {"text": "Clan War Governance System"},
        }
        return self._send_payload({"embeds": [embed]})
