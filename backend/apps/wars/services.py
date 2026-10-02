import math
from datetime import date
from typing import Any

from django.conf import settings

from apps.clans.models import Clan, Member, WarPass
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
                    "reliability_score": float(member.reliability_score),
                }
            )

        # Sort participants: most pending attacks first, then lowest reliability score, then medals
        participants_list.sort(
            key=lambda x: (x["attacks_pending"], -x["reliability_score"], x["medals"]),
            reverse=True,
        )

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


class MemberWarHistoryService:
    """Service to retrieve historical war attendance and attack logs for a member."""

    DAY_NAMES = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo",
    }

    def get_member_war_history(self, member: Member, max_races: int = 10) -> dict[str, Any]:
        """Return the detailed war attack history across the last completed and current races."""
        logs = (
            WarAttackLog.objects.filter(member=member)
            .select_related("war_day__river_race")
            .order_by("-war_day__date")
        )

        war_passes = list(member.war_passes.all())

        race_dict: dict[tuple[int, int], dict] = {}
        for log in logs:
            race = log.war_day.river_race
            key = (race.season_id, race.section_index)
            if key not in race_dict:
                if len(race_dict) >= max_races:
                    continue
                race_dict[key] = {
                    "season_id": race.season_id,
                    "section_index": race.section_index,
                    "state": race.state,
                    "logs": [],
                }
            if key in race_dict:
                race_dict[key]["logs"].append(log)

        total_races = len(race_dict)
        total_war_days = 0
        total_attacks_used = 0
        total_attacks_expected = 0
        total_medals = 0
        total_boat_attacks = 0

        races_payload = []
        for (s_id, sec_idx), r_data in race_dict.items():
            r_logs = r_data["logs"]
            r_logs.sort(key=lambda item: item.war_day.date)

            race_attacks_used = 0
            race_medals = 0
            race_boat_attacks = 0

            days_payload = []
            for log in r_logs:
                w_day = log.war_day
                has_pass = any(wp.start_date <= w_day.date <= wp.end_date for wp in war_passes)
                pass_reason = next(
                    (wp.reason for wp in war_passes if wp.start_date <= w_day.date <= wp.end_date),
                    None,
                )

                if w_day.day_type == "war":
                    total_war_days += 1
                    total_attacks_used += log.attacks_used
                    total_medals += log.medals_earned
                    total_boat_attacks += log.boat_attacks_count

                    if not has_pass and w_day.is_closed:
                        total_attacks_expected += 4

                race_attacks_used += log.attacks_used
                race_medals += log.medals_earned
                race_boat_attacks += log.boat_attacks_count

                days_payload.append(
                    {
                        "date": str(w_day.date),
                        "day_index": w_day.day_index,
                        "day_name": self.DAY_NAMES.get(w_day.day_index, f"Día {w_day.day_index}"),
                        "day_type": w_day.day_type,
                        "is_closed": w_day.is_closed,
                        "attacks_used": log.attacks_used,
                        "max_attacks": 4 if w_day.day_type == "war" else 0,
                        "medals_earned": log.medals_earned,
                        "boat_attacks_count": log.boat_attacks_count,
                        "has_war_pass": has_pass,
                        "war_pass_reason": pass_reason,
                    }
                )

            start_date = str(r_logs[0].war_day.date) if r_logs else None
            end_date = str(r_logs[-1].war_day.date) if r_logs else None
            war_days_in_race = sum(1 for log_item in r_logs if log_item.war_day.day_type == "war")

            races_payload.append(
                {
                    "season_id": s_id,
                    "section_index": sec_idx,
                    "state": r_data["state"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_attacks": race_attacks_used,
                    "max_attacks": war_days_in_race * 4,
                    "medals": race_medals,
                    "boat_attacks": race_boat_attacks,
                    "days": days_payload,
                }
            )

        attendance_rate = (
            min(100.0, round(total_attacks_used / total_attacks_expected * 100, 2))
            if total_attacks_expected > 0
            else float(member.reliability_score)
        )

        return {
            "member": {
                "tag": member.tag,
                "name": member.name,
                "role": member.role,
                "clan_tag": member.clan.tag if member.clan else None,
                "clan_name": member.clan.name if member.clan else None,
                "reliability_score": float(member.reliability_score),
                "trophies": member.trophies,
                "donations": member.donations,
                "donations_received": member.donations_received,
                "last_seen": member.last_seen.isoformat() if member.last_seen else None,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            },
            "summary": {
                "races_analyzed": total_races,
                "total_war_days": total_war_days,
                "total_attacks_used": total_attacks_used,
                "total_attacks_expected": total_attacks_expected,
                "attendance_rate": attendance_rate,
                "total_medals": total_medals,
                "total_boat_attacks": total_boat_attacks,
            },
            "races": races_payload,
        }
