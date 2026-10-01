from django.contrib import admin

from .models import Clan, Member, WarPass


@admin.register(Clan)
class ClanAdmin(admin.ModelAdmin):
    list_display = (
        "tag",
        "name",
        "medal_threshold",
        "war_day_reset_time",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("tag", "name")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("tag", "name", "clan", "role", "reliability_score", "is_active", "joined_at")
    list_filter = ("role", "is_active", "clan")
    search_fields = ("tag", "name", "clan__name")


@admin.register(WarPass)
class WarPassAdmin(admin.ModelAdmin):
    list_display = ("member", "reason", "start_date", "end_date", "created_at")
    list_filter = ("start_date", "end_date", "member__clan")
    search_fields = ("member__name", "member__tag", "reason")
