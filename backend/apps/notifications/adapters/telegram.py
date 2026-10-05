import html
import logging
from datetime import date

import httpx
from django.conf import settings

from apps.clans.models import Clan
from apps.governance.models import RosterAction

from .base import BaseNotificationAdapter, ClanWarStanding, PendingAttackItem

logger = logging.getLogger(__name__)


class TelegramNotificationAdapter(BaseNotificationAdapter):
    """Sends HTML-formatted messages to a Telegram group or channel via Bot API."""

    def __init__(self, config: dict | None = None, timeout: float = 10.0):
        self.config = config or {}
        self.bot_token = self.config.get("bot_token") or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
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

    ROLE_LABELS = {
        "leader": "👑 Líder",
        "coLeader": "⚔️ Colíder",
        "elder": "🛡️ Veterano",
        "member": "Miembro",
    }

    @staticmethod
    def _format_standings(standings: list[ClanWarStanding] | None) -> list[str]:
        if not standings:
            return []

        target = next((s for s in standings if s.is_target), None)
        if not target:
            return []

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        rank_emoji = medals.get(target.rank, f"{target.rank}º")
        target_fame_str = f"{target.fame:,}".replace(",", ".")

        leader = standings[0] if standings else None
        if target.rank == 1:
            if len(standings) > 1:
                lead_margin = target.fame - standings[1].fame
                margin_str = f"{lead_margin:,}".replace(",", ".")
                header_status = f"— ¡Líderes! (+{margin_str} ventaja)"
            else:
                header_status = "— ¡Líderes!"
        else:
            gap = (leader.fame - target.fame) if leader else 0
            gap_str = f"{gap:,}".replace(",", ".")
            leader_name = html.escape(leader.name) if leader else "1º"
            header_status = f"— a {gap_str} pts del 1º ({leader_name})"

        lines = [
            f"📊 <b>Posición en Guerra: {rank_emoji} {target.rank}º de {len(standings)} ({target_fame_str} pts) {header_status}</b>"
        ]
        for s in standings:
            s_icon = medals.get(s.rank, f"{s.rank}º")
            f_str = f"{s.fame:,}".replace(",", ".")
            name_esc = html.escape(s.name)
            if s.is_target:
                lines.append(f"• {s_icon} 👑 <b>{name_esc}</b>: {f_str} pts")
            else:
                d_str = f"{abs(s.diff):,}".replace(",", ".")
                diff_label = f"+{d_str}" if s.diff > 0 else f"-{d_str}"
                lines.append(f"• {s_icon} <b>{name_esc}</b>: {f_str} pts (<i>{diff_label}</i>)")

        lines.append("")
        return lines

    def send_pending_attacks_alert(
        self,
        clan: Clan,
        pending_items: list[PendingAttackItem],
        war_day_date: date,
        hours_left: int = 0,
        standings: list[ClanWarStanding] | None = None,
    ) -> bool:
        if not pending_items:
            return True

        # Group items
        high_risk = [item for item in pending_items if item.is_high_risk]
        zero_attacks = [item for item in pending_items if item.is_zero_attacks]
        in_progress = [item for item in pending_items if item.is_in_progress]

        # Sort each group by lowest reliability first
        high_risk.sort(key=lambda x: (x.reliability_score, 0 if x.role == "member" else 1))
        zero_attacks.sort(key=lambda x: (x.reliability_score, 0 if x.role == "member" else 1))
        in_progress.sort(key=lambda x: (x.attacks_used, x.reliability_score))

        countdown_str = (
            f"<b>{hours_left} hora{'s' if hours_left != 1 else ''}</b> (10:00 UTC)"
            if hours_left > 0
            else "<b>¡Cierre de jornada en curso!</b> (10:00 UTC)"
        )

        lines = [
            f"⚔️ <b>Recordatorio de Ataques de Guerra — {html.escape(clan.name)}</b>",
            f"📅 Jornada: <code>{war_day_date}</code> | Faltan: <b>{len(pending_items)}</b> miembros",
            f"⏰ <b>Cierre de jornada en:</b> {countdown_str}\n",
        ]

        # Append war standings if available
        standings_lines = self._format_standings(standings)
        if standings_lines:
            lines.extend(standings_lines)

        if high_risk:
            lines.append("🚨 <b>Candidatos a Reemplazo / Expulsión</b> (&lt; 50% fiabilidad):")
            for item in high_risk:
                role = self.ROLE_LABELS.get(item.role, item.role)
                lines.append(
                    f"• <b>{html.escape(item.member_name)}</b> ({role}) — <b>0/4</b> atq. | Fiab: <b>{item.reliability_score:.1f}%</b> [🚨 Riesgo]"
                )
            lines.append("")

        if zero_attacks:
            lines.append("⚠️ <b>Sin Ataques</b> (0/4 realizados):")
            for item in zero_attacks:
                role = self.ROLE_LABELS.get(item.role, item.role)
                lines.append(
                    f"• <b>{html.escape(item.member_name)}</b> ({role}) — <b>0/4</b> atq. | Fiab: <b>{item.reliability_score:.1f}%</b>"
                )
            lines.append("")

        if in_progress:
            lines.append("⏳ <b>Ataques En Progreso / Incompletos:</b>")
            for item in in_progress:
                role = self.ROLE_LABELS.get(item.role, item.role)
                lines.append(
                    f"• <b>{html.escape(item.member_name)}</b> ({role}) — Restan <b>{item.remaining_attacks}</b> ({item.attacks_used}/4) | Fiab: <b>{item.reliability_score:.1f}%</b>"
                )
            lines.append("")

        lines.append(
            "💡 <i>Consejo: Los miembros en 🚨 pueden ser sustituidos antes del cierre de las 10:00 UTC para dar cupo a nuevos jugadores.</i>"
        )

        return self._send_message("\n".join(lines))

    def send_all_attacks_completed_alert(
        self,
        clan: Clan,
        war_day_date: date,
        standings: list[ClanWarStanding] | None = None,
    ) -> bool:
        lines = [
            f"🎉 <b>¡100% de Asistencia Completado — {html.escape(clan.name)}!</b>\n",
            f"📅 Jornada: <code>{war_day_date}</code> (10:00 UTC)\n",
            "¡Todos los miembros activos del clan han realizado sus 4 ataques de guerra hoy! Excelente compromiso y disciplina del equipo.\n",
        ]
        standings_lines = self._format_standings(standings)
        if standings_lines:
            lines.extend(standings_lines)
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

    def send_test_message(self, clan: Clan) -> bool:
        text = (
            f"🔔 <b>Prueba de Canal - CR-Total</b>\n\n"
            f"Clan: <b>{html.escape(clan.name)}</b> (<code>{clan.tag}</code>)\n"
            f"Estado: ✅ <b>Conexión establecida correctamente con Telegram.</b>\n\n"
            f"Este canal está listo para recibir recordatorios de ataques y reportes de gobernanza."
        )
        return self._send_message(text)
