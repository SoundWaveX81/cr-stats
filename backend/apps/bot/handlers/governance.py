from apps.clans.models import Clan
from apps.governance.models import RosterAction


def handle_sanciones(args: list[str]) -> str:
    """List all pending governance sanctions and roster recommendations."""
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

    actions = RosterAction.objects.filter(clan=clan, status="pending").order_by("created_at")

    if not actions.exists():
        return (
            f"✅ <b>¡Todo en orden!</b> No hay acciones ni sanciones de roster pendientes "
            f"para el clan <b>{clan.name}</b>."
        )

    lines = [
        f"⚖️ <b>Acciones de Roster Pendientes — {clan.name}</b>",
        f"Total: <b>{actions.count()}</b> acciones por resolver\n",
    ]

    action_type_labels = {
        "kick": "🚨 Expulsión",
        "demote_member": "⚠️ Descenso a Miembro",
        "promote_elder": "✨ Ascenso a Veterano",
        "leadership_notice": "📢 Aviso a Liderazgo",
    }

    for action in actions:
        type_str = action_type_labels.get(action.action_type, action.get_action_type_display())
        lines.append(
            f"• <b>[ID {action.id}] {type_str}</b> → <b>{action.member.name}</b> (<code>{action.member.tag}</code>)\n"
            f"  <i>{action.reason}</i>\n"
            f"  👉 Resolver: <code>/ejecutar {action.id}</code> | <code>/descartar {action.id}</code>\n"
        )

    return "\n".join(lines)


def handle_ejecutar(args: list[str]) -> str:
    """Mark a specific roster action as executed in the Clash Royale game."""
    if not args or not args[0].isdigit():
        return "⚠️ Uso incorrecto. Especifica el ID numérico de la acción: <code>/ejecutar &lt;id&gt;</code>"

    action_id = int(args[0])
    action = RosterAction.objects.filter(id=action_id).first()

    if not action:
        return f"❌ No se encontró ninguna acción con el ID <b>#{action_id}</b>."

    if action.status == "executed":
        return f"ℹ️ La acción <b>#{action_id}</b> ya había sido marcada como ejecutada previamente."

    action.mark_executed()
    return (
        f"✅ <b>Acción ejecutada con éxito</b>\n"
        f"La propuesta de <b>{action.get_action_type_display()}</b> para "
        f"<b>{action.member.name}</b> (<code>{action.member.tag}</code>) quedó registrada como realizada."
    )


def handle_descartar(args: list[str]) -> str:
    """Dismiss a proposed disciplinary or roster recommendation."""
    if not args or not args[0].isdigit():
        return "⚠️ Uso incorrecto. Especifica el ID numérico de la acción: <code>/descartar &lt;id&gt;</code>"

    action_id = int(args[0])
    action = RosterAction.objects.filter(id=action_id).first()

    if not action:
        return f"❌ No se encontró ninguna acción con el ID <b>#{action_id}</b>."

    if action.status == "dismissed":
        return f"ℹ️ La acción <b>#{action_id}</b> ya había sido descartada previamente."

    action.mark_dismissed()
    return (
        f"🗑️ <b>Acción descartada</b>\n"
        f"La propuesta de <b>{action.get_action_type_display()}</b> para "
        f"<b>{action.member.name}</b> fue descartada por el liderazgo."
    )
