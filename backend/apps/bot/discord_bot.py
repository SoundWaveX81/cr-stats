import logging
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone

import discord
from asgiref.sync import sync_to_async
from discord.ext import commands

from apps.clans.models import Clan, Member, WarPass
from apps.governance.models import RosterAction
from apps.ingestion.services import SyncClanService, SyncRiverRaceService
from apps.notifications.models import NotificationChannel
from apps.wars.models import WarAttackLog, WarDay
from apps.wars.services import CurrentWarService

logger = logging.getLogger(__name__)


def create_discord_bot() -> commands.Bot:
    """Create and configure the interactive Discord Bot with governance commands."""
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=["!", "/"], intents=intents, help_command=None)

    @bot.event
    async def on_ready():
        logger.info(f"Bot de Discord conectado como {bot.user} (ID: {bot.user.id})")

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        logger.exception(f"Error ejecutando comando Discord '{ctx.command}': {error}")
        try:
            await ctx.send(f"❌ Error al ejecutar el comando: `{error}`")
        except Exception:
            pass

    @bot.command(name="ayuda", aliases=["help", "start"])
    async def cmd_help(ctx: commands.Context):
        embed = discord.Embed(
            title="👑 CR Total — Bot de Gobernanza de Clanes",
            description="Comandos interactivos disponibles para líderes y colíderes:",
            color=0xF5B722,  # Gold
        )
        embed.add_field(
            name="📊 Monitoreo de Guerra",
            value=(
                "• `!sincronizar <#tag>` — Sincroniza o registra un clan con Supercell.\n"
                "• `!estado [tag]` — Resumen de la River Race actual y medallas.\n"
                "• `!pendientes [tag]` — Miembros con ataques pendientes hoy."
            ),
            inline=False,
        )
        embed.add_field(
            name="⚖️ Gobernanza y Sanciones",
            value=(
                "• `!sanciones [tag]` — Lista de propuestas disciplinarias pendientes.\n"
                "• `!ejecutar <id>` — Marca la sanción como ejecutada en el juego.\n"
                "• `!descartar <id>` — Descarta una propuesta de sanción."
            ),
            inline=False,
        )
        embed.add_field(
            name="🛡️ Exenciones y Alertas",
            value=(
                "• `!exentar <#tag> <dias> <motivo>` — Otorga un Pase de Guerra.\n"
                "• `!alertas [tag] [webhook_url]` — Vincula este canal para alertas de guerra."
            ),
            inline=False,
        )
        embed.set_footer(text="Puedes usar el prefijo ! o / indiferentemente.")
        await ctx.send(embed=embed)

    @bot.command(name="sincronizar", aliases=["sync", "vincular"])
    async def cmd_sync(ctx: commands.Context, tag: str | None = None):
        async with ctx.typing():

            def _sync():
                if tag:
                    clean_tag = tag.strip().upper()
                    if not clean_tag.startswith("#"):
                        clean_tag = f"#{clean_tag}"
                    clan, _ = Clan.objects.get_or_create(
                        tag=clean_tag, defaults={"name": clean_tag}
                    )
                else:
                    clan = Clan.objects.filter(is_active=True).first()
                    if not clan:
                        return None, "Especifica el tag del clan: `!sincronizar #2PP`"

                sync_clan_service = SyncClanService()
                sync_race_service = SyncRiverRaceService()
                sync_clan_service.sync(clan)
                sync_race_service.sync(clan)
                clan.refresh_from_db()
                return clan, None

            clan, error_msg = await sync_to_async(_sync)()
            if error_msg:
                await ctx.send(f"❌ {error_msg}")
                return

            embed = discord.Embed(
                title=f"✅ Sincronización Exitosa — {clan.name}",
                description="Datos actualizados directamente desde la API oficial de Clash Royale.",
                color=0x2ECC71,
            )
            embed.add_field(name="Tag del Clan", value=f"`{clan.tag}`", inline=True)
            active_count = await sync_to_async(clan.members.filter(is_active=True).count)()
            embed.add_field(name="Miembros Activos", value=f"{active_count} / 50", inline=True)
            await ctx.send(embed=embed)

    @bot.command(name="estado", aliases=["status"])
    async def cmd_status(ctx: commands.Context, tag: str | None = None):
        def _get_status():
            clan = None
            if tag:
                clean_tag = tag.strip().upper()
                if not clean_tag.startswith("#"):
                    clean_tag = f"#{clean_tag}"
                clan = Clan.objects.filter(tag=clean_tag).first()
            else:
                clan = Clan.objects.filter(is_active=True).first()

            if not clan:
                return None, None

            war_service = CurrentWarService()
            overview = war_service.get_war_overview(clan)
            return clan, overview

        clan, overview = await sync_to_async(_get_status)()
        if not clan:
            await ctx.send(
                "❌ No se encontró ningún clan activo registrado. Usa `!sincronizar <#tag>`."
            )
            return

        clan_info = overview["clan"]
        race_info = overview["race"]
        stats_info = overview["stats"]
        clans_list = overview.get("clans", [])

        section_idx = race_info.get("section_index", 0)
        day_idx = race_info.get("day_index", 0)
        day_type = race_info.get("day_type", "training")
        is_colosseum = section_idx >= 3

        if day_type == "war":
            war_day_num = max(1, day_idx - 2)
            day_title = f"Día {war_day_num} de Guerra"
            if is_colosseum:
                day_title += " (Coliseo)"
        else:
            training_days = ["Lunes", "Martes", "Miércoles"]
            t_name = (
                training_days[day_idx] if 0 <= day_idx < len(training_days) else f"D{day_idx + 1}"
            )
            day_title = f"Día de Entrenamiento ({t_name})"

        total_used = stats_info.get("total_attacks_used", 0)
        total_possible = stats_info.get("total_attacks_possible", 200)
        total_pending = stats_info.get("total_attacks_pending", 0)
        pct = round((total_used / total_possible) * 100) if total_possible > 0 else 0

        embed = discord.Embed(
            title=f"🏰 Estado del Clan: {clan.name} ({clan.tag})",
            color=0x2B70C9,  # Clash Royale Blue
        )
        embed.add_field(
            name="Miembros", value=f"{stats_info.get('total_members', 50)} / 50", inline=True
        )
        embed.add_field(
            name="Trofeos de Guerra", value=f"{clan_info.get('clan_score', 0):,} 🏆", inline=True
        )
        embed.add_field(name="Reinicio Diario", value=f"{clan.war_day_reset_time} UTC", inline=True)

        embed.add_field(
            name=f"⚔️ Jornada de Hoy ({day_title})",
            value=(
                f"• Ataques usados: **{total_used}** / {total_possible} ({pct}%)\n"
                f"• Ataques pendientes: **{total_pending}** restantes"
            ),
            inline=False,
        )

        race_label = f"Semana {section_idx}" + (" (Coliseo)" if is_colosseum else "")
        user_pos = clan_info.get("position", 1)
        user_fame = clan_info.get("fame", 0)
        gap = stats_info.get("gap_to_first", 0)
        wins = stats_info.get("wins_needed_for_first", 0)

        race_text = (
            f"• Posición: **#{user_pos}** de {len(clans_list)} clanes\n"
            f"• Medallas Acumuladas: **{user_fame:,}**\n"
        )
        if user_pos > 1 and gap > 0:
            race_text += f"• Distancia al 1º: **-{gap:,}** medallas (~{wins} victorias)"
        elif user_pos == 1 and len(clans_list) > 1:
            second_fame = clans_list[1].get("fame", 0) if len(clans_list) > 1 else 0
            race_text += f"• Ventaja sobre el 2º: **+{user_fame - second_fame:,}** medallas"

        embed.add_field(name=f"🌊 River Race ({race_label})", value=race_text, inline=False)

        if len(clans_list) > 1:
            medals_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            leaderboard_lines = []
            for i, c in enumerate(clans_list[:5]):
                med = medals_emojis[i] if i < len(medals_emojis) else f"{i + 1}."
                marker = " 👈 (Nosotros)" if c.get("is_user_clan") else ""
                leaderboard_lines.append(
                    f"{med} **{c.get('name')}**: {c.get('fame', 0):,} medallas{marker}"
                )
            embed.add_field(
                name="📊 Clasificación en Vivo", value="\n".join(leaderboard_lines), inline=False
            )

        await ctx.send(embed=embed)

    @bot.command(name="pendientes")
    async def cmd_pending(ctx: commands.Context, tag: str | None = None):
        def _get_pending():
            clan = None
            if tag:
                clean_tag = tag.strip().upper()
                if not clean_tag.startswith("#"):
                    clean_tag = f"#{clean_tag}"
                clan = Clan.objects.filter(tag=clean_tag).first()
            else:
                clan = Clan.objects.filter(is_active=True).first()

            if not clan:
                return None, None, []

            today = date.today()
            open_day = WarDay.objects.filter(
                river_race__clan=clan, day_type="war", is_closed=False, date=today
            ).first()

            if not open_day:
                return clan, None, []

            active_members = clan.members.filter(is_active=True).order_by("role", "name")
            attack_logs = {
                log.member_id: log for log in WarAttackLog.objects.filter(war_day=open_day)
            }

            pending = []
            for m in active_members:
                if m.war_passes.filter(start_date__lte=today, end_date__gte=today).exists():
                    continue
                used = attack_logs[m.tag].attacks_used if m.tag in attack_logs else 0
                if used < 4:
                    pending.append((m.name, m.role, used, 4 - used, float(m.reliability_score)))

            # Sort: fewest attacks first (0/4), lowest reliability score first, regular members first
            pending.sort(key=lambda x: (x[2], x[4], 0 if x[1] == "member" else 1))

            return clan, open_day, pending

        clan, open_day, pending = await sync_to_async(_get_pending)()
        if not clan:
            await ctx.send("❌ No se encontró ningún clan activo registrado.")
            return

        if not open_day:
            await ctx.send(
                f"ℹ️ Hoy no hay jornada de guerra abierta para **{clan.name}** (días de entrenamiento o descanso)."
            )
            return

        if not pending:
            embed = discord.Embed(
                title="🎉 ¡Todos los ataques completados!",
                description=f"Todos los miembros activos de **{clan.name}** han completado sus 4 ataques hoy.",
                color=0x2ECC71,
            )
            await ctx.send(embed=embed)
            return

        # Calculate time remaining until 10:00 UTC daily reset
        cutoff_dt = datetime.combine(
            open_day.date + timedelta(days=1), time(10, 0), tzinfo=dt_timezone.utc
        )
        now = datetime.now(dt_timezone.utc)
        time_left = cutoff_dt - now
        total_seconds = max(0, int(time_left.total_seconds()))
        hours_left = total_seconds // 3600
        minutes_left = (total_seconds % 3600) // 60

        embed = discord.Embed(
            title=f"⚔️ Ataques Pendientes — {clan.name}",
            description=(
                f"Faltan **{len(pending)}** miembros por completar sus 4 ataques de hoy.\n"
                f"⏰ **Cierre de jornada en:** {hours_left}h {minutes_left}m (10:00 UTC)\n"
                f"*💡 Prioridad: Miembros con 🚨 tienen baja fiabilidad histórica.*"
            ),
            color=0xE74C3C,  # Red
        )
        role_labels = {
            "leader": "👑 Líder",
            "coLeader": "⚔️ Colíder",
            "elder": "🛡️ Veterano",
            "member": "Miembro",
        }
        lines = []
        for name, role, used, rem, score in pending:
            if used == 0 and score < 50.0:
                tag_label = "🚨 Alto Riesgo"
            elif used == 0:
                tag_label = "⚠️ Sin ataques"
            else:
                tag_label = "⏳ En progreso"

            lines.append(
                f"• **{name}** ({role_labels.get(role, role)}) — Restan **{rem}** ataques ({used}/4) | Fiab: **{score:.1f}%** [{tag_label}]"
            )

        chunks = []
        current_chunk = []
        current_len = 0

        for line in lines:
            line_len = len(line) + 1
            if current_len + line_len > 900 or len(current_chunk) >= 15:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        for idx, chunk in enumerate(chunks, 1):
            field_name = "Jugadores" if len(chunks) == 1 else f"Jugadores ({idx}/{len(chunks)})"
            embed.add_field(name=field_name, value=chunk, inline=False)

        await ctx.send(embed=embed)

    @bot.command(name="sanciones")
    async def cmd_sanciones(ctx: commands.Context, tag: str | None = None):
        def _get_actions():
            clan = None
            if tag:
                clean_tag = tag.strip().upper()
                if not clean_tag.startswith("#"):
                    clean_tag = f"#{clean_tag}"
                clan = Clan.objects.filter(tag=clean_tag).first()
            else:
                clan = Clan.objects.filter(is_active=True).first()

            if not clan:
                return None, []
            return clan, list(
                RosterAction.objects.filter(clan=clan, status="pending").order_by("created_at")
            )

        clan, actions = await sync_to_async(_get_actions)()
        if not clan:
            await ctx.send("❌ No se encontró ningún clan activo.")
            return

        if not actions:
            embed = discord.Embed(
                title=f"✅ Todo en orden — {clan.name}",
                description="No hay sanciones ni acciones de gobernanza pendientes.",
                color=0x2ECC71,
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"⚖️ Acciones de Roster Pendientes — {clan.name}",
            description=f"Total: **{len(actions)}** acciones por resolver:",
            color=0xF39C12,  # Amber
        )
        for a in actions[:10]:
            embed.add_field(
                name=f"[ID {a.id}] {a.get_action_type_display()} → {a.member.name}",
                value=f"Motivo: *{a.reason}*\n👉 `!ejecutar {a.id}` o `!descartar {a.id}`",
                inline=False,
            )
        await ctx.send(embed=embed)

    @bot.command(name="ejecutar")
    async def cmd_ejecutar(ctx: commands.Context, action_id: int):
        def _exec():
            action = RosterAction.objects.filter(id=action_id).first()
            if not action:
                return None, "No se encontró la acción especificada."
            if action.status == "executed":
                return action, "Esta acción ya había sido marcada como ejecutada."
            action.mark_executed()
            return action, None

        action, err = await sync_to_async(_exec)()
        if err:
            await ctx.send(f"⚠️ {err}")
        else:
            await ctx.send(
                f"✅ Acción **#{action.id}** ({action.get_action_type_display()}) para **{action.member.name}** marcada como ejecutada en el juego."
            )

    @bot.command(name="descartar")
    async def cmd_descartar(ctx: commands.Context, action_id: int):
        def _dismiss():
            action = RosterAction.objects.filter(id=action_id).first()
            if not action:
                return None, "No se encontró la acción especificada."
            if action.status == "dismissed":
                return action, "Esta acción ya había sido descartada."
            action.mark_dismissed()
            return action, None

        action, err = await sync_to_async(_dismiss)()
        if err:
            await ctx.send(f"⚠️ {err}")
        else:
            await ctx.send(f"🗑️ Acción **#{action.id}** para **{action.member.name}** descartada.")

    @bot.command(name="exentar")
    async def cmd_exentar(ctx: commands.Context, identifier: str, days: int, *, reason: str):
        def _create_pass():
            tag = identifier.strip().upper()
            if not tag.startswith("#"):
                tag = f"#{tag}"
            member = (
                Member.objects.filter(tag=tag).first()
                or Member.objects.filter(name__iexact=identifier).first()
            )
            if not member:
                return None, f"No se encontró al miembro con tag o nombre `{identifier}`."

            today = date.today()
            end_date = today + timedelta(days=days)
            p = WarPass.objects.create(
                member=member,
                reason=reason,
                start_date=today,
                end_date=end_date,
            )
            return p, None

        war_pass, err = await sync_to_async(_create_pass)()
        if err:
            await ctx.send(f"❌ {err}")
            return

        embed = discord.Embed(
            title="🎟️ Pase de Guerra Otorgado con Éxito",
            color=0x9B59B6,  # Purple
        )
        embed.add_field(
            name="Jugador", value=f"{war_pass.member.name} (`{war_pass.member.tag}`)", inline=True
        )
        embed.add_field(
            name="Vigencia",
            value=f"Del {war_pass.start_date} al {war_pass.end_date} ({days} días)",
            inline=True,
        )
        embed.add_field(name="Motivo", value=war_pass.reason, inline=False)
        await ctx.send(embed=embed)

    @bot.command(name="alertas")
    async def cmd_alertas(
        ctx: commands.Context, tag: str | None = None, webhook_url: str | None = None
    ):
        """Link this Discord channel to receive automated war attack reminders."""

        def _get_clan():
            if tag and not tag.startswith("http"):
                clean_tag = tag.strip().upper()
                if not clean_tag.startswith("#"):
                    clean_tag = f"#{clean_tag}"
                return Clan.objects.filter(tag=clean_tag).first()
            return Clan.objects.filter(is_active=True).first()

        clan = await sync_to_async(_get_clan)()
        if not clan:
            await ctx.send("❌ No se encontró ningún clan activo registrado.")
            return

        final_webhook_url = (
            webhook_url
            if (webhook_url and webhook_url.startswith("http"))
            else (tag if (tag and tag.startswith("http")) else None)
        )

        if not final_webhook_url and hasattr(ctx.channel, "create_webhook"):
            try:
                webhooks = await ctx.channel.webhooks()
                existing = next((w for w in webhooks if w.name == "CR-Total Alertas"), None)
                if existing:
                    final_webhook_url = existing.url
                else:
                    created_wh = await ctx.channel.create_webhook(name="CR-Total Alertas")
                    final_webhook_url = created_wh.url
            except Exception as exc:
                logger.warning(f"Could not auto-create Discord webhook: {exc}")

        if not final_webhook_url:
            await ctx.send(
                "❌ No se pudo crear automáticamente un Webhook en este canal (revisa los permisos del bot).\n"
                "Puedes crearlo manualmente en *Ajustes del canal > Integraciones > Webhooks* y ejecutar:\n"
                "`!alertas [tag_clan] <url_del_webhook>`"
            )
            return

        def _save_channel():
            _ch, is_new = NotificationChannel.objects.update_or_create(
                clan=clan,
                provider="discord_webhook",
                defaults={"config": {"webhook_url": final_webhook_url}, "is_active": True},
            )
            return is_new

        is_created = await sync_to_async(_save_channel)()
        action_word = "vinculado exitosamente" if is_created else "actualizado"

        embed = discord.Embed(
            title="✅ Canal de Alertas de Guerra Vinculado",
            description=(
                f"Este canal ha sido {action_word} para recibir los recordatorios automáticos del clan "
                f"**{clan.name}** (`{clan.tag}`).\n\n"
                f"⏰ **Horarios de envío (Jueves a Domingo):**\n"
                f"• 06:00 UTC (quedan 4 horas)\n"
                f"• 07:00 UTC (quedan 3 horas)\n"
                f"• 08:00 UTC (quedan 2 horas)\n"
                f"• 09:00 UTC (queda 1 hora)\n"
                f"• 10:00 UTC (cierre de jornada / confirmación final)"
            ),
            color=0x2ECC71,
        )
        await ctx.send(embed=embed)

    return bot
