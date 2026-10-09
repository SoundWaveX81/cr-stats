from datetime import datetime, time, timedelta
from datetime import timezone as dt_timezone

from apps.clans.models import Clan
from apps.wars.models import WarAttackLog, WarDay


def handle_pending(args: list[str]) -> str:
    """Return the list of members who have not completed all 4 war attacks today."""
    clan = None
    if args:
        tag = args[0].strip().upper()
        if not tag.startswith("#"):
            tag = f"#{tag}"
        clan = Clan.objects.filter(tag=tag).first()
        if not clan:
            return f"❌ No se encontró ningún clan con el tag <code>{tag}</code>."
    else:
        clan = Clan.objects.filter(is_active=True).first()
        if not clan:
            return "❌ No hay clanes activos registrados en el sistema."

    today = clan.get_current_war_date()
    open_war_day = WarDay.objects.filter(
        river_race__clan=clan,
        day_type="war",
        is_closed=False,
        date=today,
    ).first()

    if not open_war_day:
        return (
            f"ℹ️ Hoy (<b>{today}</b>) no hay una jornada de guerra abierta registrada para "
            f"<b>{clan.name}</b>. Recuerda que los lunes a miércoles son días de entrenamiento."
        )

    active_members = clan.members.filter(is_active=True)
    attack_logs = {log.member_id: log for log in WarAttackLog.objects.filter(war_day=open_war_day)}

    pending_list = []
    for member in active_members:
        # Check if exempt by WarPass
        has_pass = member.war_passes.filter(
            start_date__lte=open_war_day.date,
            end_date__gte=open_war_day.date,
        ).exists()
        if has_pass:
            continue

        log = attack_logs.get(member.tag)
        used = log.attacks_used if log else 0
        if used < 4:
            pending_list.append((member, used, 4 - used))

    if not pending_list:
        return (
            f"🎉 <b>¡Excelente!</b> Todos los miembros activos de <b>{clan.name}</b> "
            f"han completado sus 4 ataques de guerra hoy ({today})."
        )

    # Calculate countdown until daily reset (10:00 UTC of next day)
    cutoff_dt = datetime.combine(
        open_war_day.date + timedelta(days=1), time(10, 0), tzinfo=dt_timezone.utc
    )
    now = datetime.now(dt_timezone.utc)
    time_left = cutoff_dt - now
    total_seconds = max(0, int(time_left.total_seconds()))
    hours_left = total_seconds // 3600
    minutes_left = (total_seconds % 3600) // 60

    # Sort: fewest attacks first (0/4), lowest reliability score first, members before elders
    pending_list.sort(
        key=lambda x: (
            x[1],  # attacks used asc (0 first)
            x[0].reliability_score,  # lowest reliability first
            0 if x[0].role == "member" else 1,  # regular members first
        )
    )

    lines = [
        f"⚔️ <b>Ataques Pendientes Hoy — {clan.name}</b>",
        f"📅 Fecha: <b>{open_war_day.date}</b> | Faltan: <b>{len(pending_list)}</b> miembros",
        f"⏰ <b>Cierre de jornada en:</b> {hours_left}h {minutes_left}m (10:00 UTC)\n",
    ]

    for member, used, remaining in pending_list:
        role_labels = {
            "leader": "👑 Líder",
            "coLeader": "⚔️ Colíder",
            "elder": "🛡️ Veterano",
            "member": "Miembro",
        }
        role_label = role_labels.get(member.role, member.role)
        score = float(member.reliability_score)

        if used == 0 and score < 50.0:
            status_tag = "🚨 Alto Riesgo"
        elif used == 0:
            status_tag = "⚠️ Sin ataques"
        else:
            status_tag = "⏳ En progreso"

        lines.append(
            f"• <b>{member.name}</b> ({role_label}) — Restan <b>{remaining}</b> ataques ({used}/4) | Fiab: <b>{score:.1f}%</b> [{status_tag}]"
        )

    lines.append(
        "\n💡 <i>Prioridad: Miembros con 🚨 tienen baja fiabilidad histórica y ningún ataque hoy (candidatos a reemplazo antes del cierre).</i>"
    )

    return "\n".join(lines)
