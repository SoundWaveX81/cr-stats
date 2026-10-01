from django.contrib import admin

from .models import RiverRace, WarAttackLog, WarDay


@admin.register(RiverRace)
class RiverRaceAdmin(admin.ModelAdmin):
    list_display = ("clan", "season_id", "section_index", "state", "clan_score", "updated_at")
    list_filter = ("clan", "season_id", "state")
    search_fields = ("clan__name", "clan__tag")


@admin.register(WarDay)
class WarDayAdmin(admin.ModelAdmin):
    list_display = ("river_race", "date", "day_index", "day_type", "is_closed")
    list_filter = ("day_type", "is_closed", "river_race__clan")
    search_fields = ("river_race__clan__name",)


@admin.register(WarAttackLog)
class WarAttackLogAdmin(admin.ModelAdmin):
    list_display = ("war_day", "member", "attacks_used", "medals_earned", "boat_attacks_count")
    list_filter = ("attacks_used", "boat_attacks_count", "war_day__day_type")
    search_fields = ("member__name", "member__tag")
