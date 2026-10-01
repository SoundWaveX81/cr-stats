from datetime import date

from django.db import transaction

from apps.clans.models import Clan, Member
from apps.ingestion.client import ClashRoyaleClient
from apps.wars.models import RiverRace, WarAttackLog, WarDay


class SyncRiverRaceService:
    """Service to synchronize River Race state, daily war schedule, and member attacks."""

    def __init__(self, client: ClashRoyaleClient | None = None):
        self.client = client or ClashRoyaleClient()

    @transaction.atomic
    def sync(self, clan: Clan, target_date: date | None = None) -> tuple[RiverRace, WarDay]:
        if target_date is None:
            target_date = date.today()

        data = self.client.get_current_river_race(clan.tag)

        section_index = data.get("sectionIndex", 0)
        period_index = data.get("periodIndex", 0)
        day_index = period_index % 7

        # Days 0, 1, 2 are training days; 3, 4, 5, 6 are war days
        day_type = "war" if day_index >= 3 else "training"

        clan_data = data.get("clan", {})
        clan_score = clan_data.get("fame", clan_data.get("clanScore", 0))
        season_id = data.get("seasonId", 1)

        river_race, _ = RiverRace.objects.update_or_create(
            clan=clan,
            season_id=season_id,
            section_index=section_index,
            defaults={
                "state": data.get("state", "matched"),
                "clan_score": clan_score,
            },
        )

        war_day, _ = WarDay.objects.update_or_create(
            river_race=river_race,
            date=target_date,
            defaults={
                "day_index": day_index,
                "day_type": day_type,
            },
        )

        participants = clan_data.get("participants", [])
        for p in participants:
            raw_tag = p["tag"]
            clean_tag = raw_tag.strip().upper()
            if not clean_tag.startswith("#"):
                clean_tag = f"#{clean_tag}"

            member, _ = Member.objects.get_or_create(
                tag=clean_tag,
                defaults={
                    "clan": clan,
                    "name": p.get("name", "Desconocido"),
                    "role": "member",
                    "is_active": False,
                },
            )

            attacks_used = p.get("decksUsedToday", p.get("decksUsed", 0))
            decks_used = p.get("decksUsed", 0)
            fame = p.get("fame", 0)
            boat_attacks = p.get("boatAttacks", 0)

            WarAttackLog.objects.update_or_create(
                war_day=war_day,
                member=member,
                defaults={
                    "attacks_used": attacks_used,
                    "decks_used": decks_used,
                    "medals_earned": fame,
                    "boat_attacks_count": boat_attacks,
                },
            )

        return river_race, war_day
