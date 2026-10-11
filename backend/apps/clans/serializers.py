from datetime import date

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Clan, Member, UserProfile, WarPass


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


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    is_superuser = serializers.BooleanField(source="user.is_superuser", read_only=True)
    clan_tag = serializers.CharField(source="clan.tag", read_only=True, default=None)
    clan_name = serializers.CharField(source="clan.name", read_only=True, default=None)
    player_tag = serializers.CharField(source="player.tag", read_only=True, default=None)
    player_name = serializers.CharField(source="player.name", read_only=True, default=None)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "username",
            "email",
            "is_superuser",
            "role",
            "clan_tag",
            "clan_name",
            "player_tag",
            "player_name",
        ]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        profile = getattr(user, "profile", None)
        token["username"] = user.username
        token["is_superuser"] = user.is_superuser
        token["role"] = (
            profile.role if profile else ("clan_admin" if user.is_superuser else "member")
        )
        token["clan_tag"] = profile.clan.tag if (profile and profile.clan) else None
        token["clan_name"] = profile.clan.name if (profile and profile.clan) else None
        token["player_tag"] = profile.player.tag if (profile and profile.player) else None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        profile = getattr(user, "profile", None)
        data["user"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_superuser": user.is_superuser,
            "role": profile.role if profile else ("clan_admin" if user.is_superuser else "member"),
            "clan_tag": profile.clan.tag if (profile and profile.clan) else None,
            "clan_name": profile.clan.name if (profile and profile.clan) else None,
            "player_tag": profile.player.tag if (profile and profile.player) else None,
            "player_name": profile.player.name if (profile and profile.player) else None,
        }
        return data
