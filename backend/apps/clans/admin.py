from django.contrib import admin

from apps.notifications.models import WarAlertPreference

from .models import Clan, Member, WarPass


class WarAlertPreferenceInline(admin.StackedInline):
    model = WarAlertPreference
    can_delete = False
    verbose_name = "Preferencia de Alertas de Guerra"
    verbose_name_plural = "Preferencia de Alertas de Guerra"
    readonly_fields = ("updated_at",)
    extra = 0


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
    inlines = [WarAlertPreferenceInline]


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
