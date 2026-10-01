import logging

from apps.clans.models import Clan
from apps.ingestion.services import SyncClanService, SyncRiverRaceService

logger = logging.getLogger(__name__)


def handle_sync(args: list[str]) -> str:
    """Synchronize a clan's roster and river race on demand via Clash Royale API."""
    clan = None
    if args:
        tag = args[0].strip().upper()
        if not tag.startswith("#"):
            tag = f"#{tag}"
        clan, _ = Clan.objects.get_or_create(tag=tag, defaults={"name": tag})
    else:
        clan = Clan.objects.filter(is_active=True).first()
        if not clan:
            return (
                "⚠️ Especifica el tag del clan a sincronizar.\n"
                "Ejemplo: <code>/sincronizar #2PP</code>"
            )

    try:
        sync_clan_service = SyncClanService()
        sync_race_service = SyncRiverRaceService()

        sync_clan_service.sync(clan)
        sync_race_service.sync(clan)
        clan.refresh_from_db()

        members_count = clan.members.filter(is_active=True).count()
        return (
            f"✅ <b>¡Sincronización Exitosa!</b>\n\n"
            f"🏰 Clan: <b>{clan.name}</b> (<code>{clan.tag}</code>)\n"
            f"👥 Miembros activos actualizados: <b>{members_count}</b>\n"
            f"🌊 Datos de la River Race al día.\n\n"
            f"Ya puedes consultar <code>/estado</code> o <code>/pendientes</code>."
        )
    except Exception as exc:
        logger.exception(f"Error syncing clan {clan.tag} via bot: {exc}")
        return (
            f"❌ <b>Error durante la sincronización</b>\n"
            f"No se pudo sincronizar el clan <code>{clan.tag}</code> con Supercell.\n"
            f"Detalle: <i>{exc}</i>"
        )
