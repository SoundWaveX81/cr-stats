from django.contrib import admin

from .models import RosterAction


@admin.register(RosterAction)
class RosterActionAdmin(admin.ModelAdmin):
    list_display = ("member", "clan", "action_type", "status", "created_at", "executed_at")
    list_filter = ("action_type", "status", "clan")
    search_fields = ("member__name", "member__tag", "reason")
    actions = ["mark_as_executed", "mark_as_dismissed"]

    @admin.action(description="Marcar como ejecutada en el juego")
    def mark_as_executed(self, request, queryset):
        for action in queryset:
            action.mark_executed()

    @admin.action(description="Descartar acción")
    def mark_as_dismissed(self, request, queryset):
        for action in queryset:
            action.mark_dismissed()
