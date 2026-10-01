from datetime import date

from rest_framework import serializers

from .models import Clan, Member, WarPass


class MemberSerializer(serializers.ModelSerializer):
    reliability_score = serializers.FloatField(read_only=True)

    class Meta:
        model = Member
        fields = [
            "tag",
            "name",
            "role",
            "reliability_score",
            "trophies",
            "donations",
            "donations_received",
            "last_seen",
            "is_active",
            "joined_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ClanSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = Clan
        fields = [
            "tag",
            "name",
            "medal_threshold",
            "war_day_reset_time",
            "is_active",
            "members_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class WarPassSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.name", read_only=True)
    is_active_now = serializers.SerializerMethodField()

    class Meta:
        model = WarPass
        fields = [
            "id",
            "member",
            "member_name",
            "reason",
            "start_date",
            "end_date",
            "is_active_now",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_is_active_now(self, obj) -> bool:
        return obj.is_active_on(date.today())
