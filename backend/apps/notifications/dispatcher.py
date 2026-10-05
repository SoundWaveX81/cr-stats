import logging
from datetime import date

from django.conf import settings

from apps.clans.models import Clan
from apps.governance.models import RosterAction
from apps.notifications.adapters import (
    BaseNotificationAdapter,
    ClanWarStanding,
    ConsoleNotificationAdapter,
    DiscordWebhookNotificationAdapter,
    PendingAttackItem,
    TelegramNotificationAdapter,
)
from apps.notifications.models import NotificationChannel

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches neutral domain events to all active notification adapters configured for a clan."""

    @staticmethod
    def get_adapter(channel: NotificationChannel) -> BaseNotificationAdapter | None:
        """Instantiate the concrete adapter for a given channel."""
        if channel.provider == "console":
            return ConsoleNotificationAdapter(channel.config)
        if channel.provider == "discord_webhook":
            return DiscordWebhookNotificationAdapter(channel.config)
        if channel.provider == "telegram":
            return TelegramNotificationAdapter(channel.config)
        logger.warning(f"Unknown notification provider: {channel.provider}")
        return None

    def get_adapters_for_clan(
        self, clan: Clan
    ) -> list[tuple[NotificationChannel | str, BaseNotificationAdapter]]:
        """Return all instantiated adapters for the clan's active channels with env fallback."""
        channels = list(clan.notification_channels.filter(is_active=True))
        adapters = []
        has_telegram = False
        has_discord = False

        for ch in channels:
            adapter = self.get_adapter(ch)
            if adapter:
                adapters.append((ch, adapter))
                if ch.provider == "telegram":
                    has_telegram = True
                elif ch.provider == "discord_webhook":
                    has_discord = True

        # Fallback to default environment variables if not explicitly registered in DB
        default_tg_chat = getattr(settings, "DEFAULT_TELEGRAM_CHAT_ID", "")
        tg_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not has_telegram and default_tg_chat and tg_token:
            adapters.append(
                (
                    "env_telegram",
                    TelegramNotificationAdapter(
                        {"chat_id": default_tg_chat, "bot_token": tg_token}
                    ),
                )
            )

        default_discord_url = getattr(settings, "DEFAULT_DISCORD_WEBHOOK_URL", "")
        if not has_discord and default_discord_url:
            adapters.append(
                (
                    "env_discord",
                    DiscordWebhookNotificationAdapter({"webhook_url": default_discord_url}),
                )
            )

        return adapters

    def dispatch_pending_attacks(
        self,
        clan: Clan,
        pending_items: list[PendingAttackItem],
        war_day_date: date,
        hours_left: int = 0,
        standings: list[ClanWarStanding] | None = None,
    ) -> dict[int | str, bool]:
        """Send pending attacks alerts to all configured clan channels."""
        results = {}
        for channel, adapter in self.get_adapters_for_clan(clan):
            ch_key = channel.id if isinstance(channel, NotificationChannel) else channel
            try:
                success = adapter.send_pending_attacks_alert(
                    clan,
                    pending_items,
                    war_day_date,
                    hours_left=hours_left,
                    standings=standings,
                )
                results[ch_key] = success
            except Exception as exc:
                logger.exception(f"Unexpected error dispatching to channel {ch_key}: {exc}")
                results[ch_key] = False
        return results

    def dispatch_all_attacks_completed(
        self,
        clan: Clan,
        war_day_date: date,
        standings: list[ClanWarStanding] | None = None,
    ) -> dict[int | str, bool]:
        """Send 100% completion notice to all configured clan channels."""
        results = {}
        for channel, adapter in self.get_adapters_for_clan(clan):
            ch_key = channel.id if isinstance(channel, NotificationChannel) else channel
            try:
                success = adapter.send_all_attacks_completed_alert(
                    clan, war_day_date, standings=standings
                )
                results[ch_key] = success
            except Exception as exc:
                logger.exception(f"Unexpected error dispatching to channel {ch_key}: {exc}")
                results[ch_key] = False
        return results

    def dispatch_roster_report(
        self, clan: Clan, actions: list[RosterAction], war_day_date: date
    ) -> dict[int | str, bool]:
        """Send daily governance report to all configured clan channels."""
        results = {}
        for channel, adapter in self.get_adapters_for_clan(clan):
            ch_key = channel.id if isinstance(channel, NotificationChannel) else channel
            try:
                success = adapter.send_daily_roster_report(clan, actions, war_day_date)
                results[ch_key] = success
            except Exception as exc:
                logger.exception(f"Unexpected error dispatching to channel {ch_key}: {exc}")
                results[ch_key] = False
        return results

    def dispatch_leadership_notices(
        self, clan: Clan, notices: list[RosterAction]
    ) -> dict[int | str, bool]:
        """Send leadership notices to all configured clan channels."""
        results = {}
        for channel, adapter in self.get_adapters_for_clan(clan):
            ch_key = channel.id if isinstance(channel, NotificationChannel) else channel
            try:
                success = adapter.send_leadership_notice(clan, notices)
                results[ch_key] = success
            except Exception as exc:
                logger.exception(f"Unexpected error dispatching to channel {ch_key}: {exc}")
                results[ch_key] = False
        return results

    def dispatch_test_message(self, clan: Clan) -> dict[int | str, bool]:
        """Send test message to all configured clan channels."""
        results = {}
        for channel, adapter in self.get_adapters_for_clan(clan):
            ch_key = channel.id if isinstance(channel, NotificationChannel) else channel
            try:
                success = adapter.send_test_message(clan)
                results[ch_key] = success
            except Exception as exc:
                logger.exception(f"Unexpected error sending test to channel {ch_key}: {exc}")
                results[ch_key] = False
        return results
