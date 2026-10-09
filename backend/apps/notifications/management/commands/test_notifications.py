from django.core.management.base import BaseCommand

from apps.clans.models import Clan
from apps.notifications.dispatcher import NotificationDispatcher
from apps.notifications.models import NotificationChannel


class Command(BaseCommand):
    help = "Test configured notification channels (Telegram, Discord, Console) or force pending attacks reminder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clan",
            type=str,
            help="Filter by clan tag (e.g. #P8CCG2UJ)",
        )
        parser.add_argument(
            "--send-pending",
            action="store_true",
            help="Force sending the actual pending attacks alert instead of a test ping",
        )
        parser.add_argument(
            "--provider",
            type=str,
            choices=["telegram", "discord_webhook", "console"],
            help="Filter by specific notification provider",
        )

    def handle(self, *args, **options):
        clan_tag = options.get("clan")
        send_pending = options.get("send_pending")
        provider_filter = options.get("provider")

        if clan_tag and not clan_tag.startswith("#"):
            clan_tag = f"#{clan_tag}"

        clans = (
            Clan.objects.filter(tag=clan_tag, is_active=True)
            if clan_tag
            else Clan.objects.filter(is_active=True)
        )

        if not clans.exists():
            self.stdout.write(
                self.style.ERROR(f"No active clan found matching '{clan_tag or 'any'}'.")
            )
            return

        dispatcher = NotificationDispatcher()

        for clan in clans:
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"\n--- Probando Clan: {clan.name} ({clan.tag}) ---")
            )
            channels = clan.notification_channels.filter(is_active=True)
            if provider_filter:
                channels = channels.filter(provider=provider_filter)

            if not channels.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"No hay canales de notificación activos en BD para {clan.name} con los filtros dados."
                    )
                )

            adapters = dispatcher.get_adapters_for_clan(clan)
            if provider_filter:
                adapters = [
                    (ch, ad)
                    for (ch, ad) in adapters
                    if (isinstance(ch, NotificationChannel) and ch.provider == provider_filter)
                    or (isinstance(ch, str) and provider_filter in ch)
                ]

            if not adapters:
                self.stdout.write(
                    self.style.ERROR(
                        "No se encontraron adaptadores configurados con los filtros dados."
                    )
                )
                continue

            if send_pending:
                self.stdout.write(
                    "Sincronizando y forzando envío de alerta de ataques pendientes..."
                )

                from apps.ingestion.services import SyncRiverRaceService
                from apps.notifications.adapters.base import PendingAttackItem
                from apps.wars.models import WarAttackLog, WarDay

                try:
                    SyncRiverRaceService().sync(clan)
                except Exception as exc:
                    self.stdout.write(
                        self.style.WARNING(f"Aviso: no se pudo sincronizar en vivo: {exc}")
                    )

                effective_today = clan.get_current_war_date()
                open_war_day = (
                    WarDay.objects.filter(
                        river_race__clan=clan, day_type="war", is_closed=False, date=effective_today
                    ).first()
                    or WarDay.objects.filter(river_race__clan=clan, day_type="war")
                    .order_by("-date")
                    .first()
                )
                if not open_war_day:
                    self.stdout.write(self.style.ERROR("No se encontró jornada de guerra."))
                    continue

                active_members = clan.members.filter(is_active=True)
                attack_logs = {
                    log.member_id: log for log in WarAttackLog.objects.filter(war_day=open_war_day)
                }
                pending_items = []
                for member in active_members:
                    if member.war_passes.filter(
                        start_date__lte=open_war_day.date, end_date__gte=open_war_day.date
                    ).exists():
                        continue
                    used = (
                        attack_logs.get(member.tag).attacks_used
                        if attack_logs.get(member.tag)
                        else 0
                    )
                    if used < 4:
                        pending_items.append(
                            PendingAttackItem(
                                member_tag=member.tag,
                                member_name=member.name,
                                role=member.role,
                                attacks_used=used,
                                remaining_attacks=4 - used,
                                reliability_score=float(member.reliability_score),
                            )
                        )

                standings = (
                    open_war_day.river_race.get_standings_objects()
                    if open_war_day and open_war_day.river_race
                    else []
                )

                for ch, adapter in adapters:
                    ch_desc = (
                        f"{ch.get_provider_display()} (ID: {ch.id})"
                        if isinstance(ch, NotificationChannel)
                        else str(ch)
                    )
                    self.stdout.write(f"Despachando alerta a: {ch_desc} ... ", ending="")
                    try:
                        ok = (
                            adapter.send_pending_attacks_alert(
                                clan,
                                pending_items,
                                open_war_day.date,
                                hours_left=0,
                                standings=standings,
                            )
                            if pending_items
                            else adapter.send_all_attacks_completed_alert(
                                clan, open_war_day.date, standings=standings
                            )
                        )
                        if ok:
                            self.stdout.write(self.style.SUCCESS("[OK]"))
                        else:
                            self.stdout.write(self.style.ERROR("[ERROR]"))
                    except Exception as exc:
                        self.stdout.write(self.style.ERROR(f"[EXCEPCIÓN: {exc}]"))
            else:
                for ch, adapter in adapters:
                    ch_desc = (
                        f"{ch.get_provider_display()} (ID: {ch.id})"
                        if isinstance(ch, NotificationChannel)
                        else str(ch)
                    )
                    self.stdout.write(f"Enviando mensaje de prueba a: {ch_desc} ... ", ending="")
                    try:
                        success = adapter.send_test_message(clan)
                        if success:
                            self.stdout.write(self.style.SUCCESS("[OK - ENVIADO]"))
                        else:
                            self.stdout.write(self.style.ERROR("[ERROR - FALLÓ EL ENVÍO]"))
                    except Exception as exc:
                        self.stdout.write(self.style.ERROR(f"[EXCEPCIÓN: {exc}]"))
