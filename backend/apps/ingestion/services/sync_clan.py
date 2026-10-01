from datetime import datetime
from datetime import timezone as dt_timezone

from django.db import transaction
from django.utils import timezone

from apps.clans.models import Clan, Member
from apps.ingestion.client import ClashRoyaleClient


def parse_last_seen(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        try:
            return datetime.strptime(val, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=dt_timezone.utc)
        except Exception:
            return None


class SyncClanService:
    """Service to synchronize Clan details and member roster from Clash Royale API."""

    def __init__(self, client: ClashRoyaleClient | None = None):
        self.client = client or ClashRoyaleClient()

    @transaction.atomic
    def sync(self, clan: Clan) -> Clan:
        data = self.client.get_clan(clan.tag)

        # Update clan metadata
        clan.name = data.get("name", clan.name)
        clan.save(update_fields=["name", "updated_at"])

        active_tags = set()
        member_list = data.get("memberList", [])
        now = timezone.now()

        for item in member_list:
            raw_tag = item["tag"]
            clean_tag = raw_tag.strip().upper()
            if not clean_tag.startswith("#"):
                clean_tag = f"#{clean_tag}"

            active_tags.add(clean_tag)
            trophies = int(item.get("trophies", 0) or 0)
            donations = int(item.get("donations", 0) or 0)
            donations_received = int(item.get("donationsReceived", 0) or 0)
            last_seen = parse_last_seen(item.get("lastSeen"))

            member = Member.objects.filter(tag=clean_tag).first()
            if not member:
                Member.objects.create(
                    tag=clean_tag,
                    clan=clan,
                    name=item.get("name", "Desconocido"),
                    role=item.get("role", "member"),
                    trophies=trophies,
                    donations=donations,
                    donations_received=donations_received,
                    last_seen=last_seen,
                    is_active=True,
                    joined_at=now,
                )
            else:
                update_fields = [
                    "clan",
                    "name",
                    "role",
                    "trophies",
                    "donations",
                    "donations_received",
                    "last_seen",
                    "is_active",
                    "updated_at",
                ]
                if not member.is_active:
                    member.joined_at = now
                    update_fields.append("joined_at")
                elif not member.joined_at:
                    member.joined_at = member.created_at
                    update_fields.append("joined_at")

                member.clan = clan
                member.name = item.get("name", "Desconocido")
                member.role = item.get("role", "member")
                member.trophies = trophies
                member.donations = donations
                member.donations_received = donations_received
                member.last_seen = last_seen
                member.is_active = True
                member.save(update_fields=update_fields)

        # Mark members as inactive if they have left or been kicked from the clan
        clan.members.exclude(tag__in=active_tags).update(is_active=False)
        return clan
