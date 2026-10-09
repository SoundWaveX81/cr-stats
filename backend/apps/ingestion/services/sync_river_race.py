from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone

from django.db import transaction

from apps.clans.models import Clan, Member
from apps.ingestion.client import ClashRoyaleClient
from apps.wars.helpers import extract_clan_fame
from apps.wars.models import RiverRace, WarAttackLog, WarDay


class SyncRiverRaceService:
    """Service to synchronize River Race state, daily war schedule, and member attacks."""

    def __init__(self, client: ClashRoyaleClient | None = None):
        self.client = client or ClashRoyaleClient()

    @transaction.atomic
    def sync(self, clan: Clan, target_date: date | None = None) -> tuple[RiverRace, WarDay]:
        if target_date is None:
            target_date = clan.get_current_war_date()

        data = self.client.get_current_river_race(clan.tag)

        section_index = data.get("sectionIndex", 0)
        period_index = data.get("periodIndex", 0)
        day_index = period_index % 7

        # Days 0, 1, 2 are training days; 3, 4, 5, 6 are war days
        day_type = "war" if day_index >= 3 else "training"

        clan_data = data.get("clan", {})
        clan_score = extract_clan_fame(clan_data)
        season_id = data.get("seasonId")
        if not season_id:
            # 1. If today's war day was already created, reuse its race's season
            existing_race_today = (
                RiverRace.objects.filter(clan=clan, war_days__date=target_date)
                .exclude(season_id=1)
                .first()
            )
            if existing_race_today:
                season_id = existing_race_today.season_id
            else:
                # 2. Check if an active race is currently in progress
                active_race = (
                    RiverRace.objects.filter(clan=clan)
                    .exclude(state="clans_finished")
                    .exclude(season_id=1)
                    .order_by("-season_id", "-section_index")
                    .first()
                )
                if active_race:
                    if active_race.section_index == section_index:
                        season_id = active_race.season_id
                    else:
                        # Week transitioned
                        active_race.state = "clans_finished"
                        active_race.war_days.filter(is_closed=False).update(is_closed=True)
                        active_race.save(update_fields=["state"])
                        try:
                            self.sync_race_history(clan)
                        except Exception:
                            pass

                        if section_index > active_race.section_index:
                            season_id = active_race.season_id
                        else:
                            season_id = active_race.season_id + 1
                else:
                    # 3. No active race; deduce from latest completed race
                    latest_completed = (
                        RiverRace.objects.filter(clan=clan, state="clans_finished")
                        .exclude(season_id=1)
                        .order_by("-season_id", "-section_index")
                        .first()
                    )
                    if not latest_completed:
                        try:
                            self.sync_race_history(clan)
                            latest_completed = (
                                RiverRace.objects.filter(clan=clan, state="clans_finished")
                                .exclude(season_id=1)
                                .order_by("-season_id", "-section_index")
                                .first()
                            )
                        except Exception:
                            pass

                    if latest_completed:
                        if section_index > latest_completed.section_index:
                            season_id = latest_completed.season_id
                        else:
                            season_id = latest_completed.season_id + 1
                    else:
                        season_id = 1

        raw_clans = list(data.get("clans", []))
        if clan_data and not any(c.get("tag") == clan.tag for c in raw_clans):
            raw_clans.append(clan_data)

        clans_with_fame = []
        for c in raw_clans:
            c_fame = extract_clan_fame(c)
            clans_with_fame.append((c, c_fame))

        clans_with_fame.sort(
            key=lambda item: (
                item[1],
                item[0].get("clanScore", 0),
            ),
            reverse=True,
        )
        standings = [
            {
                "rank": idx + 1,
                "tag": c.get("tag"),
                "name": c.get("name"),
                "fame": fame,
                "clan_score": c.get("clanScore", 0),
                "badge_id": c.get("badgeId"),
            }
            for idx, (c, fame) in enumerate(clans_with_fame)
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
            day_index=day_index,
            defaults={
                "date": target_date,
                "day_type": day_type,
            },
        )

        # Ensure any earlier war days in this race are marked closed
        river_race.war_days.filter(day_index__lt=day_index, is_closed=False).update(is_closed=True)

        participants = clan_data.get("participants", [])

        # In Clash Royale API, fame and boatAttacks are cumulative totals for the participant
        # across the entire river race. Prefetch previous war day logs in this race to store
        # true daily incremental medals and boat attacks.
        prev_logs_by_member: dict[str, dict[str, int]] = {}
        for prev_log in WarAttackLog.objects.filter(
            war_day__river_race=river_race,
            war_day__day_index__lt=day_index,
        ).values("member_id", "medals_earned", "boat_attacks_count"):
            m_id = prev_log["member_id"]
            if m_id not in prev_logs_by_member:
                prev_logs_by_member[m_id] = {"medals": 0, "boat": 0}
            prev_logs_by_member[m_id]["medals"] += prev_log["medals_earned"]
            prev_logs_by_member[m_id]["boat"] += prev_log["boat_attacks_count"]

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
            cum_fame = p.get("fame", 0)
            cum_boat_attacks = p.get("boatAttacks", 0)

            prev_data = prev_logs_by_member.get(clean_tag, {"medals": 0, "boat": 0})
            daily_medals = max(0, cum_fame - prev_data["medals"])
            daily_boat = max(0, cum_boat_attacks - prev_data["boat"])

            WarAttackLog.objects.update_or_create(
                war_day=war_day,
                member=member,
                defaults={
                    "attacks_used": attacks_used,
                    "decks_used": decks_used,
                    "medals_earned": daily_medals,
                    "boat_attacks_count": daily_boat,
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
                    clan_score = extract_clan_fame(c)
                    break

            if not clan_data:
                continue

            raw_standings = sorted(
                item.get("standings", []),
                key=lambda s: s.get("rank", 999),
            )
            standings = [
                {
                    "rank": s.get("rank"),
                    "tag": s.get("clan", {}).get("tag"),
                    "name": s.get("clan", {}).get("name"),
                    "fame": extract_clan_fame(s.get("clan", {})),
                    "clan_score": s.get("clan", {}).get("clanScore", 0),
                    "badge_id": s.get("clan", {}).get("badgeId"),
                }
                for s in raw_standings
            ]

            river_race, _ = RiverRace.objects.update_or_create(
                clan=clan,
                season_id=season_id,
                section_index=section_index,
                defaults={
                    "state": "clans_finished",
                    "clan_score": clan_score,
                    "standings": standings,
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
