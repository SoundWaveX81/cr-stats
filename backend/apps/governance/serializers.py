from rest_framework import serializers

from .models import RosterAction


class RosterActionSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.name", read_only=True)
    clan_name = serializers.CharField(source="clan.name", read_only=True)
    action_type_display = serializers.CharField(source="get_action_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RosterAction
        fields = [
            "id",
            "clan",
            "clan_name",
            "member",
            "member_name",
            "war_day",
            "action_type",
            "action_type_display",
            "status",
            "status_display",
            "reason",
            "created_at",
            "executed_at",
        ]
        read_only_fields = ["created_at", "executed_at"]
