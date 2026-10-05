from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone

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

        raw_clans = data.get("clans", [])
        sorted_clans = sorted(
            raw_clans,
            key=lambda c: (
                c.get("fame", 0),
                c.get("clanScore", 0),
            ),
            reverse=True,
        )
        standings = [
            {
                "rank": idx + 1,
                "tag": c.get("tag"),
                "name": c.get("name"),
                "fame": c.get("fame", 0),
                "clan_score": c.get("clanScore", 0),
                "badge_id": c.get("badgeId"),
            }
            for idx, c in enumerate(sorted_clans)
        ]

        river_race, _ = RiverRace.objects.update_or_create(
            clan=clan,
            season_id=season_id,
            section_index=section_index,
            defaults={
                "state": data.get("state", "matched"),
                "clan_score": clan_score,
                "standings": standings,
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

    @transaction.atomic
    def sync_race_history(self, clan: Clan) -> int:
        """Fetch and ingest completed river races from /v1/clans/{clanTag}/riverracelog.

        Creates closed WarDay objects and WarAttackLog records for each past war day,
        ensuring historical attendance reliability is accurate and complete.
        """
        data = self.client.get_river_race_log(clan.tag)
        items = data.get("items", [])
        if not items:
            return 0

        races_synced = 0
        for item in reversed(items):
            season_id = item.get("seasonId")
            section_index = item.get("sectionIndex")
            created_date_str = item.get("createdDate")
            if not created_date_str or season_id is None or section_index is None:
                continue

            try:
                end_monday = datetime.strptime(created_date_str[:8], "%Y%m%d").date()
            except ValueError:
                continue

            clan_data = None
            clan_score = 0
            for standing in item.get("standings", []):
                c = standing.get("clan", {})
                if c.get("tag") == clan.tag:
                    clan_data = c
                    clan_score = c.get("fame", c.get("clanScore", 0))
                    break

            if not clan_data:
                continue

            river_race, _ = RiverRace.objects.update_or_create(
                clan=clan,
                season_id=season_id,
                section_index=section_index,
                defaults={
                    "state": "clans_finished",
                    "clan_score": clan_score,
                },
            )
            races_synced += 1

            war_days = []
            for offset, d_idx in [(4, 3), (3, 4), (2, 5), (1, 6)]:
                w_date = end_monday - timedelta(days=offset)
                w_day, _ = WarDay.objects.update_or_create(
                    river_race=river_race,
                    date=w_date,
                    defaults={
                        "day_index": d_idx,
                        "day_type": "war",
                        "is_closed": True,
                    },
                )
                war_days.append(w_day)

            participants = clan_data.get("participants", [])
            first_war_date = war_days[0].date
            first_war_dt = datetime.combine(
                first_war_date, datetime.min.time(), tzinfo=dt_timezone.utc
            )

            for p in participants:
                raw_tag = p.get("tag", "").strip().upper()
                if not raw_tag.startswith("#"):
                    raw_tag = f"#{raw_tag}"

                decks_used = p.get("decksUsed", 0)
                fame = p.get("fame", 0)
                boat_attacks = p.get("boatAttacks", 0)

                member, created = Member.objects.get_or_create(
                    tag=raw_tag,
                    defaults={
                        "clan": clan,
                        "name": p.get("name", "Desconocido"),
                        "role": "member",
                        "is_active": False,
                        "joined_at": first_war_dt,
                    },
                )
                if not created and (not member.joined_at or member.joined_at > first_war_dt):
                    member.joined_at = first_war_dt
                    member.save(update_fields=["joined_at", "updated_at"])

                for idx, w_day in enumerate(war_days):
                    day_attacks = min(max(decks_used - (idx * 4), 0), 4)
                    day_fame = fame // 4
                    day_boat = 1 if boat_attacks > idx else 0

                    WarAttackLog.objects.update_or_create(
                        war_day=w_day,
                        member=member,
                        defaults={
                            "attacks_used": day_attacks,
                            "decks_used": day_attacks,
                            "medals_earned": day_fame,
                            "boat_attacks_count": day_boat,
                        },
                    )

        # Recalculate historical reliability scores over the newly ingested history
        from apps.governance.services.engine import GovernanceEngineService

        engine = GovernanceEngineService()
        engine.update_reliability_scores(clan)

        return races_synced
