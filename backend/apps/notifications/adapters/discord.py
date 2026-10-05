import logging
from datetime import date, datetime, timezone

import httpx

from apps.clans.models import Clan
from apps.governance.models import RosterAction

from .base import BaseNotificationAdapter, ClanWarStanding, PendingAttackItem

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

    ROLE_LABELS = {
        "leader": "👑 Líder",
        "coLeader": "⚔️ Colíder",
        "elder": "🛡️ Veterano",
        "member": "Miembro",
    }

    @staticmethod
    def _format_standings_field(standings: list[ClanWarStanding] | None) -> dict | None:
        if not standings:
            return None

        target = next((s for s in standings if s.is_target), None)
        if not target:
            return None

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        rank_emoji = medals.get(target.rank, f"{target.rank}º")
        target_fame_str = f"{target.fame:,}".replace(",", ".")

        leader = standings[0] if standings else None
        if target.rank == 1:
            if len(standings) > 1:
                lead_margin = target.fame - standings[1].fame
                margin_str = f"{lead_margin:,}".replace(",", ".")
                header_status = f"👑 ¡Líderes! (+{margin_str} pts de ventaja)"
            else:
                header_status = "👑 ¡Líderes!"
        else:
            gap = (leader.fame - target.fame) if leader else 0
            gap_str = f"{gap:,}".replace(",", ".")
            header_status = f"A {gap_str} pts del 1º ({leader.name})"

        field_title = f"📊 Clasificación: {rank_emoji} {target.rank}º de {len(standings)} ({target_fame_str} pts)"
        field_lines = [f"_{header_status}_"]

        for s in standings:
            s_icon = medals.get(s.rank, f"{s.rank}º")
            f_str = f"{s.fame:,}".replace(",", ".")
            if s.is_target:
                field_lines.append(f"• {s_icon} 👑 **{s.name}**: {f_str} pts")
            else:
                d_str = f"{abs(s.diff):,}".replace(",", ".")
                diff_label = f"+{d_str}" if s.diff > 0 else f"-{d_str}"
                field_lines.append(f"• {s_icon} **{s.name}**: {f_str} pts (`{diff_label}`)")

        return {
            "name": field_title[:256],
            "value": "\n".join(field_lines)[:1024],
            "inline": False,
        }

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

        # Color based on severity
        if high_risk:
            embed_color = COLOR_RED
        elif zero_attacks:
            embed_color = COLOR_ORANGE
        else:
            embed_color = COLOR_YELLOW

        countdown_str = (
            f"**{hours_left} hora{'s' if hours_left != 1 else ''}** (10:00 UTC)"
            if hours_left > 0
            else "**¡Cierre de jornada en curso!** (10:00 UTC)"
        )

        fields = []

        # Add standings field first if available
        standings_field = self._format_standings_field(standings)
        if standings_field:
            fields.append(standings_field)

        if high_risk:
            val_lines = [
                f"• **{item.member_name}** ({self.ROLE_LABELS.get(item.role, item.role)}) — **0/4** | Fiab: **{item.reliability_score:.1f}%**"
                for item in high_risk
            ]
            fields.append(
                {
                    "name": f"🚨 Candidatos a Reemplazo / Expulsión ({len(high_risk)})",
                    "value": "\n".join(val_lines)[:1024],
                    "inline": False,
                }
            )

        if zero_attacks:
            val_lines = [
                f"• **{item.member_name}** ({self.ROLE_LABELS.get(item.role, item.role)}) — **0/4** | Fiab: **{item.reliability_score:.1f}%**"
                for item in zero_attacks
            ]
            fields.append(
                {
                    "name": f"⚠️ Sin Ataques ({len(zero_attacks)})",
                    "value": "\n".join(val_lines)[:1024],
                    "inline": False,
                }
            )

        if in_progress:
            val_lines = [
                f"• **{item.member_name}** ({self.ROLE_LABELS.get(item.role, item.role)}) — Faltan **{item.remaining_attacks}** ({item.attacks_used}/4) | Fiab: **{item.reliability_score:.1f}%**"
                for item in in_progress
            ]
            fields.append(
                {
                    "name": f"⏳ En Progreso / Incompletos ({len(in_progress)})",
                    "value": "\n".join(val_lines)[:1024],
                    "inline": False,
                }
            )

        embed = {
            "title": f"⚔️ Recordatorio: Ataques Pendientes de Guerra — {clan.name}",
            "description": (
                f"📅 Jornada: **{war_day_date}** | Faltan **{len(pending_items)}** miembros\n"
                f"⏰ **Cierre de jornada en:** {countdown_str}"
            ),
            "color": embed_color,
            "fields": fields,
            "footer": {
                "text": "Prioridad: Miembros en 🚨 pueden ser sustituidos antes del cierre de las 10:00 UTC"
            },
        }
        return self._send_payload({"embeds": [embed]})

    def send_all_attacks_completed_alert(
        self,
        clan: Clan,
        war_day_date: date,
        standings: list[ClanWarStanding] | None = None,
    ) -> bool:
        fields = []
        standings_field = self._format_standings_field(standings)
        if standings_field:
            fields.append(standings_field)

        embed = {
            "title": f"🎉 ¡100% de Asistencia Completado — {clan.name}!",
            "description": (
                f"📅 Jornada del **{war_day_date}** (10:00 UTC).\n\n"
                "¡Todos los miembros activos del clan han realizado sus 4 ataques de guerra hoy!\n"
                "Excelente compromiso y disciplina del equipo."
            ),
            "color": COLOR_GREEN,
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

    def send_test_message(self, clan: Clan) -> bool:
        now_iso = datetime.now(timezone.utc).isoformat()
        embed = {
            "title": "🔔 Prueba de Canal - CR-Total",
            "description": (
                f"**Clan:** {clan.name} (`{clan.tag}`)\n"
                f"**Estado:** ✅ **Conexión establecida correctamente con Discord.**\n\n"
                f"Este canal está listo para recibir recordatorios de ataques y reportes de gobernanza."
            ),
            "color": COLOR_GREEN,
            "timestamp": now_iso,
            "footer": {"text": "CR-Total • Test de Integración"},
        }
        return self._send_payload({"embeds": [embed]})
