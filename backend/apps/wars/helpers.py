from typing import Any


def extract_clan_fame(clan_dict: dict[str, Any] | None) -> int:
    """
    Extract total war fame/medals for a clan from Clash Royale API data.

    In Clash Royale River Race API:
    - During active war days, clan['fame'] is often 0 while points are accumulated
      in participant fame and/or clan['periodPoints'].
    - Participants' fame is cumulative across the entire race.
    - Concluded races store total points in clan['fame'].
    """
    if not clan_dict or not isinstance(clan_dict, dict):
        return 0

    participants = clan_dict.get("participants") or []
    if participants:
        p_fame = sum(p.get("fame", 0) for p in participants if isinstance(p, dict))
        if p_fame > 0:
            return p_fame

    fame = clan_dict.get("fame") or 0
    period_points = clan_dict.get("periodPoints") or 0

    if fame > 0 and period_points > 0:
        return max(fame, fame + period_points if fame < period_points else fame)

    return fame or period_points or 0
