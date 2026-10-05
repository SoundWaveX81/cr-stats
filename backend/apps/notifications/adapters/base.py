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
    reliability_score: float = 100.0

    @property
    def is_high_risk(self) -> bool:
        """High risk: 0 attacks and reliability below 50%."""
        return self.attacks_used == 0 and self.reliability_score < 50.0

    @property
    def is_zero_attacks(self) -> bool:
        """Zero attacks with moderate/high reliability."""
        return self.attacks_used == 0 and self.reliability_score >= 50.0

    @property
    def is_in_progress(self) -> bool:
        """In progress: 1 to 3 attacks used."""
        return 0 < self.attacks_used < 4


@dataclass(frozen=True)
class ClanWarStanding:
    """Represents a clan's ranking and points in the current river race."""

    rank: int
    tag: str
    name: str
    fame: int
    is_target: bool = False
    diff: int = 0  # Points difference relative to our clan (> 0 ahead, < 0 behind)


class BaseNotificationAdapter(ABC):
    """Abstract interface defining the multi-provider notification adapter contract."""

    @abstractmethod
    def send_pending_attacks_alert(
        self,
        clan: Clan,
        pending_items: list[PendingAttackItem],
        war_day_date: date,
        hours_left: int = 0,
        standings: list[ClanWarStanding] | None = None,
    ) -> bool:
        """Send reminder alert for members with pending attacks before day reset."""

    @abstractmethod
    def send_all_attacks_completed_alert(
        self,
        clan: Clan,
        war_day_date: date,
        standings: list[ClanWarStanding] | None = None,
    ) -> bool:
        """Send congratulatory notice when 100% of clan attacks are completed."""

    @abstractmethod
    def send_daily_roster_report(
        self, clan: Clan, actions: list[RosterAction], war_day_date: date
    ) -> bool:
        """Send consolidated daily report of sanctions and recommended promotions."""

    @abstractmethod
    def send_leadership_notice(self, clan: Clan, notices: list[RosterAction]) -> bool:
        """Send informational compliance notice directed to clan leaders."""

    @abstractmethod
    def send_test_message(self, clan: Clan) -> bool:
        """Send a test notification message to verify channel connectivity."""
