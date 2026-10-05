from django.conf import settings

from apps.clans.models import Clan
from apps.notifications.models import NotificationChannel


def handle_alertas(args: list[str], chat_id: int | str | None = None) -> str:
    """Link the current Telegram chat to receive automated hourly war reminders for a clan."""
    if not chat_id:
        return "❌ No se pudo determinar el ID de este chat."

    clan = None
    if args:
        clean_tag = args[0].strip().upper()
        if not clean_tag.startswith("#"):
            clean_tag = f"#{clean_tag}"
        clan = Clan.objects.filter(tag=clean_tag).first()
        if not clan:
            return f"❌ No se encontró ningún clan con el tag <code>{clean_tag}</code>."
    else:
        clan = Clan.objects.filter(is_active=True).first()
        if not clan:
            return "❌ No hay ningún clan activo registrado en el sistema."

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")

    _channel, created = NotificationChannel.objects.update_or_create(
        clan=clan,
        provider="telegram",
        defaults={
            "config": {"chat_id": str(chat_id), "bot_token": bot_token},
            "is_active": True,
        },
    )

    action_text = "vinculado exitosamente" if created else "actualizado"
    return (
        f"✅ <b>Canal de Alertas Configurado</b>\n\n"
        f"Este chat (ID: <code>{chat_id}</code>) ha sido {action_text} para el clan <b>{clan.name}</b> (<code>{clan.tag}</code>).\n\n"
        f"⏰ Recibirás alertas automáticas durante los <b>Días de Guerra (Jueves 10:00 UTC a Lunes 10:00 UTC)</b> "
        f"según la frecuencia y horarios configurados para el clan en Django Admin."
    )
