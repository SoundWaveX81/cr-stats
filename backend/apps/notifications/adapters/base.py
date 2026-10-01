from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from apps.clans.models import Clan
from apps.governance.models import RosterAction


@dataclass(frozen=True)
class PendingAttackItem:
    """Neutral domain representation of a member with pending war attacks."""

    member_tag: str
    member_name: str
    role: str
    attacks_used: int
    remaining_attacks: int


class BaseNotificationAdapter(ABC):
    """Abstract interface defining the multi-provider notification adapter contract."""

    @abstractmethod
    def send_pending_attacks_alert(
        self, clan: Clan, pending_items: list[PendingAttackItem], war_day_date: date
    ) -> bool:
        """Send reminder alert for members with pending attacks before day reset."""

    @abstractmethod
    def send_daily_roster_report(
        self, clan: Clan, actions: list[RosterAction], war_day_date: date
    ) -> bool:
        """Send consolidated daily report of sanctions and recommended promotions."""

    @abstractmethod
    def send_leadership_notice(self, clan: Clan, notices: list[RosterAction]) -> bool:
        """Send informational compliance notice directed to clan leaders."""
