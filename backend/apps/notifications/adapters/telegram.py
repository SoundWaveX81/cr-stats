import html
import logging
from datetime import date

import httpx

from apps.clans.models import Clan
from apps.governance.models import RosterAction

from .base import BaseNotificationAdapter, PendingAttackItem

logger = logging.getLogger(__name__)


class TelegramNotificationAdapter(BaseNotificationAdapter):
    """Sends HTML-formatted messages to a Telegram group or channel via Bot API."""

    def __init__(self, config: dict | None = None, timeout: float = 10.0):
        self.config = config or {}
        self.bot_token = self.config.get("bot_token", "")
        self.chat_id = self.config.get("chat_id", "")
        self.timeout = timeout

    def _send_message(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot_token or chat_id not configured.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    return True
                logger.error(f"Telegram API failed with HTTP {resp.status_code}: {resp.text}")
                return False
        except httpx.HTTPError as exc:
            logger.error(f"Network error calling Telegram API: {exc}")
            return False

    def send_pending_attacks_alert(
        self, clan: Clan, pending_items: list[PendingAttackItem], war_day_date: date
    ) -> bool:
        if not pending_items:
            return True

        lines = [
            f"⚠️ <b>Recordatorio de Ataques de Guerra - {html.escape(clan.name)}</b>",
            f"Jornada: <code>{war_day_date}</code>",
            "¡Quedan pocas horas antes del reinicio a las 10:00 UTC!\n",
            "<b>Miembros pendientes:</b>",
        ]
        for item in pending_items:
            lines.append(
                f"• <b>{html.escape(item.member_name)}</b> ({item.role}): "
                f"{item.attacks_used}/4 ataques (Faltan {item.remaining_attacks})"
            )

        return self._send_message("\n".join(lines))

    def send_daily_roster_report(
        self, clan: Clan, actions: list[RosterAction], war_day_date: date
    ) -> bool:
        lines = [
            f"🛡️ <b>Reporte de Gobernanza - {html.escape(clan.name)}</b>",
            f"Jornada: <code>{war_day_date}</code>\n",
        ]
        if not actions:
            lines.append(
                "✅ <i>¡100% de asistencia! Todos los miembros completaron sus ataques.</i>"
            )
        else:
            lines.append("<b>Acciones disciplinarias y ascensos propuestos:</b>")
            for act in actions:
                lines.append(
                    f"• <b>[{act.get_action_type_display()}]</b> {html.escape(act.member.name)}\n"
                    f"  <i>Motivo:</i> {html.escape(act.reason)}"
                )

        return self._send_message("\n".join(lines))

    def send_leadership_notice(self, clan: Clan, notices: list[RosterAction]) -> bool:
        if not notices:
            return True

        lines = [
            f"👑 <b>Aviso de Cumplimiento a Líderes - {html.escape(clan.name)}</b>\n",
            "Se registraron faltas de ataques en el equipo de liderazgo (exentos de sanción):",
        ]
        for notice in notices:
            lines.append(
                f"• <b>{html.escape(notice.member.name)}</b> ({notice.member.get_role_display()}): "
                f"{html.escape(notice.reason)}"
            )

        return self._send_message("\n".join(lines))
