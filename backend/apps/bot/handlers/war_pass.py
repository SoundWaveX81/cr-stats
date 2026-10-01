from datetime import date, timedelta

from apps.clans.models import Member, WarPass


def handle_exentar(args: list[str]) -> str:
    """Grant a temporary WarPass exemption to a clan member directly from chat."""
    if len(args) < 3:
        return (
            "⚠️ <b>Uso incorrecto</b>\n"
            "Sintaxis: <code>/exentar &lt;#tag_o_nombre&gt; &lt;dias&gt; &lt;motivo&gt;</code>\n"
            "Ejemplo: <code>/exentar #2P9YQ 4 Exámenes finales de universidad</code>"
        )

    target_identifier = args[0].strip()
    try:
        days = int(args[1])
        if days <= 0 or days > 30:
            return "⚠️ La cantidad de días debe ser un número entero positivo entre 1 y 30."
    except ValueError:
        return (
            f"⚠️ La cantidad de días debe ser un número válido, recibiste: <code>{args[1]}</code>."
        )

    reason = " ".join(args[2:]).strip()
    if not reason:
        return "⚠️ Debes ingresar un motivo o justificación para el pase."

    # Look up member by tag or name
    tag_candidate = target_identifier.upper()
    if not tag_candidate.startswith("#"):
        tag_candidate = f"#{tag_candidate}"

    member = Member.objects.filter(tag=tag_candidate).first()
    if not member:
        member = Member.objects.filter(name__iexact=target_identifier).first()

    if not member:
        return f"❌ No se encontró ningún miembro con el tag o nombre <code>{target_identifier}</code>."

    today = date.today()
    end_date = today + timedelta(days=days)

    pass_obj = WarPass.objects.create(
        member=member,
        reason=reason,
        start_date=today,
        end_date=end_date,
    )

    return (
        "🎟️ <b>Pase de Guerra Otorgado con Éxito</b>\n\n"
        f"👤 Jugador: <b>{member.name}</b> (<code>{member.tag}</code>)\n"
        f"🏰 Clan: <b>{member.clan.name}</b>\n"
        f"📅 Vigencia: Del <b>{pass_obj.start_date}</b> al <b>{pass_obj.end_date}</b> ({days} días)\n"
        f"📝 Motivo: <i>{reason}</i>\n\n"
        "🛡️ <i>El jugador queda automáticamente exento de sanciones durante este periodo.</i>"
    )
