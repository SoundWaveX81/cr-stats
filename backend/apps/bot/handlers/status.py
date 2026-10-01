from apps.clans.models import Clan
from apps.wars.services import CurrentWarService


def handle_status(args: list[str]) -> str:
    """Return the current war, standings, and roster status for the specified or default clan."""
    clan = None
    if args:
        tag = args[0].strip().upper()
        if not tag.startswith("#"):
            tag = f"#{tag}"
        clan = Clan.objects.filter(tag=tag).first()
        if not clan:
            return (
                f"❌ No se encontró ningún clan con el tag <code>{tag}</code> en la base de datos.\n"
                f"👉 Puedes registrarlo ejecutando: <code>/sincronizar {tag}</code>"
            )
    else:
        clan = Clan.objects.filter(is_active=True).first()
        if not clan:
            return (
                "❌ No hay ningún clan registrado aún en el sistema.\n"
                "👉 Registra tu clan ejecutando: <code>/sincronizar &lt;#tag&gt;</code> (ej. <code>/sincronizar #2PP</code>)"
            )

    war_service = CurrentWarService()
    overview = war_service.get_war_overview(clan)

    clan_info = overview["clan"]
    race_info = overview["race"]
    stats_info = overview["stats"]
    clans_list = overview.get("clans", [])

    section_idx = race_info.get("section_index", 0)
    day_idx = race_info.get("day_index", 0)
    day_type = race_info.get("day_type", "training")
    is_colosseum = section_idx >= 3

    # Format day description
    if day_type == "war":
        war_day_num = max(1, day_idx - 2)
        day_title = f"Día {war_day_num} de Guerra"
        if is_colosseum:
            day_title += " (Coliseo)"
    else:
        training_days = ["Lunes", "Martes", "Miércoles"]
        t_name = training_days[day_idx] if 0 <= day_idx < len(training_days) else f"D{day_idx + 1}"
        day_title = f"Día de Entrenamiento ({t_name})"

    # Attacks calculation
    total_attacks_used = stats_info.get("total_attacks_used", 0)
    total_attacks_possible = stats_info.get("total_attacks_possible", 200)
    attacks_pct = (
        round((total_attacks_used / total_attacks_possible) * 100)
        if total_attacks_possible > 0
        else 0
    )
    total_pending = stats_info.get("total_attacks_pending", 0)

    # Clan score / war trophies
    war_trophies = clan_info.get("clan_score", 0)
    user_fame = clan_info.get("fame", 0)
    user_pos = clan_info.get("position", 1)
    total_competing = clan_info.get("total_clans", len(clans_list))

    race_section_label = f"Semana {section_idx}" + (" (Coliseo)" if is_colosseum else "")

    lines = [
        f"🏰 <b>Estado del Clan: {clan.name}</b> (<code>{clan.tag}</code>)\n",
        f"👥 Miembros Activos: <b>{stats_info.get('total_members', 50)}</b> / 50",
        f"🏆 Trofeos de Guerra: <b>{war_trophies:,}</b>",
        f"🎯 Umbral de Ascenso: <b>{clan.medal_threshold}</b> medallas",
        f"⏰ Reinicio diario: <b>{clan.war_day_reset_time} UTC</b>\n",
        f"⚔️ <b>Jornada de Hoy: {day_title}</b>",
        f"• Ataques usados: <b>{total_attacks_used}</b> / {total_attacks_possible} ({attacks_pct}%)",
        f"• Ataques pendientes: <b>{total_pending}</b> restantes\n",
        f"🌊 <b>River Race ({race_section_label}):</b>",
        f"• Posición actual: <b>#{user_pos}</b> de {total_competing} clanes",
        f"• Medallas Acumuladas: <b>{user_fame:,}</b>",
    ]

    gap = stats_info.get("gap_to_first", 0)
    wins = stats_info.get("wins_needed_for_first", 0)
    if user_pos > 1 and gap > 0:
        lines.append(f"• Distancia al 1º: <b>-{gap:,}</b> medallas (~{wins} victorias)")
    elif user_pos == 1 and total_competing > 1:
        second_fame = clans_list[1].get("fame", 0) if len(clans_list) > 1 else 0
        lead = user_fame - second_fame
        if lead > 0:
            lines.append(f"• Ventaja sobre el 2º: <b>+{lead:,}</b> medallas")

    # Leaderboard (if more than 1 clan)
    if len(clans_list) > 1:
        medals_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        lines.append("\n📊 <b>Clasificación en la Carrera:</b>")
        for i, c in enumerate(clans_list[:5]):
            medal = medals_emojis[i] if i < len(medals_emojis) else f"{i+1}."
            is_us = c.get("is_user_clan", False)
            marker = " 👈 <i>(Nosotros)</i>" if is_us else ""
            lines.append(
                f"{medal} <b>{c.get('name')}</b>: <b>{c.get('fame', 0):,}</b> medallas{marker}"
            )

    return "\n".join(lines)

