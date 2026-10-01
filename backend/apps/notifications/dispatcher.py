import logging
from datetime import date

from apps.clans.models import Clan
from apps.governance.models import RosterAction
from apps.notifications.adapters import (
    BaseNotificationAdapter,
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
    ) -> list[tuple[NotificationChannel, BaseNotificationAdapter]]:
        """Return all instantiated adapters for the clan's active channels."""
        channels = clan.notification_channels.filter(is_active=True)
        adapters = []
        for ch in channels:
            adapter = self.get_adapter(ch)
            if adapter:
                adapters.append((ch, adapter))
        return adapters

    def dispatch_pending_attacks(
        self, clan: Clan, pending_items: list[PendingAttackItem], war_day_date: date
    ) -> dict[int, bool]:
        """Send pending attacks alerts to all configured clan channels."""
        results = {}
        for channel, adapter in self.get_adapters_for_clan(clan):
            try:
                success = adapter.send_pending_attacks_alert(clan, pending_items, war_day_date)
                results[channel.id] = success
            except Exception as exc:
                logger.exception(f"Unexpected error dispatching to channel {channel.id}: {exc}")
                results[channel.id] = False
        return results

    def dispatch_roster_report(
        self, clan: Clan, actions: list[RosterAction], war_day_date: date
    ) -> dict[int, bool]:
        """Send daily governance report to all configured clan channels."""
        results = {}
        for channel, adapter in self.get_adapters_for_clan(clan):
            try:
                success = adapter.send_daily_roster_report(clan, actions, war_day_date)
                results[channel.id] = success
            except Exception as exc:
                logger.exception(f"Unexpected error dispatching to channel {channel.id}: {exc}")
                results[channel.id] = False
        return results

    def dispatch_leadership_notices(
        self, clan: Clan, notices: list[RosterAction]
    ) -> dict[int, bool]:
        """Send leadership notices to all configured clan channels."""
        results = {}
        for channel, adapter in self.get_adapters_for_clan(clan):
            try:
                success = adapter.send_leadership_notice(clan, notices)
                results[channel.id] = success
            except Exception as exc:
                logger.exception(f"Unexpected error dispatching to channel {channel.id}: {exc}")
                results[channel.id] = False
        return results
