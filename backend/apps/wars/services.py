import math
from datetime import date
from typing import Any

from django.conf import settings

from apps.clans.models import Clan, WarPass
from apps.ingestion.client import ClashRoyaleClient
from apps.wars.models import RiverRace, WarAttackLog, WarDay


class CurrentWarService:
    """Service to compute live River Race standings, member attacks, and potential points."""

    def __init__(self, client: ClashRoyaleClient | None = None):
        self.client = client or ClashRoyaleClient()

    def get_war_overview(self, clan: Clan) -> dict[str, Any]:
        today = date.today()
        # Active war passes for this clan today
        active_passes = {
            wp.member.tag: wp.reason
            for wp in WarPass.objects.filter(
                member__clan=clan, start_date__lte=today, end_date__gte=today
            ).select_related("member")
        }

        # Active members in the database
        active_members_dict = {m.tag: m for m in clan.members.filter(is_active=True)}

        if getattr(settings, "TESTING", False):
            return self._build_from_db(clan, active_members_dict, active_passes)

        try:
            live_data = self.client.get_current_river_race(clan.tag)
            return self._build_from_live(clan, live_data, active_members_dict, active_passes)
        except Exception:
            return self._build_from_db(clan, active_members_dict, active_passes)

    def _build_from_live(
        self,
        clan: Clan,
        data: dict[str, Any],
        active_members_dict: dict[str, Any],
        active_passes: dict[str, str],
    ) -> dict[str, Any]:
        section_index = data.get("sectionIndex", 0)
        period_index = data.get("periodIndex", 0)
        day_index = period_index % 7
        day_type = "war" if day_index >= 3 else "training"
        state = data.get("state", "matched")

        # Competing clans
        raw_clans = list(data.get("clans", []))
        if not any(c.get("tag") == clan.tag for c in raw_clans):
            raw_clans.append(data.get("clan", {}))

        # Rank clans by fame desc, then clanScore desc
        ranked = sorted(
            raw_clans,
            key=lambda x: (x.get("fame", 0), x.get("clanScore", 0)),
            reverse=True,
        )

        clans_list = []
        user_rank = 1
        user_fame = 0
        first_place_fame = ranked[0].get("fame", 0) if ranked else 0

        for idx, rc in enumerate(ranked, 1):
            is_me = rc.get("tag") == clan.tag
            fame = rc.get("fame", 0)
            if is_me:
                user_rank = idx
                user_fame = fame
            clans_list.append(
                {
                    "rank": idx,
                    "tag": rc.get("tag"),
                    "name": rc.get("name"),
                    "badge_id": rc.get("badgeId"),
                    "fame": fame,
                    "clan_score": rc.get("clanScore", 0),
                    "is_user_clan": is_me,
                }
            )

        # Process participants
        clan_data = data.get("clan", {})
        participants_data = clan_data.get("participants", [])
        participants_map = {p.get("tag"): p for p in participants_data}

        participants_list = []
        total_attacks_used = 0

        for tag, member in active_members_dict.items():
            p_data = participants_map.get(tag, {})
            attacks_used = p_data.get("decksUsedToday", p_data.get("decksUsed", 0))
            attacks_used = min(4, max(0, attacks_used))
            attacks_pending = max(0, 4 - attacks_used)
            medals = p_data.get("fame", 0)
            boat_attacks = p_data.get("boatAttacks", 0)

            total_attacks_used += attacks_used
            has_pass = tag in active_passes

            participants_list.append(
                {
                    "tag": member.tag,
                    "name": member.name,
                    "role": member.role,
                    "attacks_used": attacks_used,
                    "attacks_pending": attacks_pending,
                    "medals": medals,
                    "boat_attacks": boat_attacks,
                    "has_war_pass": has_pass,
                    "war_pass_reason": active_passes.get(tag),
                }
            )

        # Sort participants: most pending attacks first, then medals
        participants_list.sort(key=lambda x: (x["attacks_pending"], -x["medals"]), reverse=True)

        total_members_count = len(active_members_dict)
        total_attacks_possible = total_members_count * 4
        total_attacks_pending = max(0, total_attacks_possible - total_attacks_used)

        potential_points_max = total_attacks_pending * 900
        potential_max_fame = user_fame + potential_points_max
        gap_to_first = max(0, first_place_fame - user_fame)
        wins_needed_for_first = math.ceil(gap_to_first / 900) if gap_to_first > 0 else 0

        return {
            "clan": {
                "tag": clan.tag,
                "name": clan.name,
                "fame": user_fame,
                "clan_score": clan_data.get("clanScore", clan.medal_threshold),
                "position": user_rank,
                "total_clans": len(clans_list),
            },
            "race": {
                "state": state,
                "section_index": section_index,
                "period_index": period_index,
                "day_index": day_index,
                "day_type": day_type,
            },
            "stats": {
                "total_members": total_members_count,
                "total_attacks_possible": total_attacks_possible,
                "total_attacks_used": total_attacks_used,
                "total_attacks_pending": total_attacks_pending,
                "potential_points_max": potential_points_max,
                "potential_max_fame": potential_max_fame,
                "first_place_fame": first_place_fame,
                "gap_to_first": gap_to_first,
                "wins_needed_for_first": wins_needed_for_first,
            },
            "clans": clans_list,
            "participants": participants_list,
        }

    def _build_from_db(
        self,
        clan: Clan,
        active_members_dict: dict[str, Any],
        active_passes: dict[str, str],
    ) -> dict[str, Any]:
        race = RiverRace.objects.filter(clan=clan).order_by("-season_id", "-section_index").first()
        war_day = WarDay.objects.filter(river_race=race).order_by("-date").first() if race else None

        section_index = race.section_index if race else 0
        state = race.state if race else "unknown"
        user_fame = race.clan_score if race else 0
        day_type = war_day.day_type if war_day else "war"
        day_index = war_day.day_index if war_day else 3

        logs = (
            {
                log.member.tag: log
                for log in WarAttackLog.objects.filter(war_day=war_day).select_related("member")
            }
            if war_day
            else {}
        )

        participants_list = []
        total_attacks_used = 0

        for tag, member in active_members_dict.items():
            log = logs.get(tag)
            attacks_used = log.attacks_used if log else 0
            attacks_pending = max(0, 4 - attacks_used)
            medals = log.medals_earned if log else 0
            boat_attacks = log.boat_attacks_count if log else 0

            total_attacks_used += attacks_used
            has_pass = tag in active_passes

            participants_list.append(
                {
                    "tag": member.tag,
                    "name": member.name,
                    "role": member.role,
                    "attacks_used": attacks_used,
                    "attacks_pending": attacks_pending,
                    "medals": medals,
                    "boat_attacks": boat_attacks,
                    "has_war_pass": has_pass,
                    "war_pass_reason": active_passes.get(tag),
                }
            )

        participants_list.sort(key=lambda x: (x["attacks_pending"], -x["medals"]), reverse=True)
        total_members_count = len(active_members_dict)
        total_attacks_possible = total_members_count * 4
        total_attacks_pending = max(0, total_attacks_possible - total_attacks_used)
        potential_points_max = total_attacks_pending * 900
        potential_max_fame = user_fame + potential_points_max

        return {
            "clan": {
                "tag": clan.tag,
                "name": clan.name,
                "fame": user_fame,
                "clan_score": clan.medal_threshold,
                "position": 1,
                "total_clans": 1,
            },
            "race": {
                "state": state,
                "section_index": section_index,
                "period_index": day_index,
                "day_index": day_index,
                "day_type": day_type,
            },
            "stats": {
                "total_members": total_members_count,
                "total_attacks_possible": total_attacks_possible,
                "total_attacks_used": total_attacks_used,
                "total_attacks_pending": total_attacks_pending,
                "potential_points_max": potential_points_max,
                "potential_max_fame": potential_max_fame,
                "first_place_fame": user_fame,
                "gap_to_first": 0,
                "wins_needed_for_first": 0,
            },
            "clans": [
                {
                    "rank": 1,
                    "tag": clan.tag,
                    "name": clan.name,
                    "badge_id": 0,
                    "fame": user_fame,
                    "clan_score": clan.medal_threshold,
                    "is_user_clan": True,
                }
            ],
            "participants": participants_list,
        }
