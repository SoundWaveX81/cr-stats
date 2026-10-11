from django.contrib import admin

from .models import RosterAction


@admin.register(RosterAction)
class RosterActionAdmin(admin.ModelAdmin):
    list_display = ("member", "clan", "action_type", "status", "created_at", "executed_at")
    list_filter = ("action_type", "status", "clan")
    search_fields = ("member__name", "member__tag", "reason")
    actions = ["mark_as_executed", "mark_as_dismissed"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.clan:
            return qs.filter(clan=request.user.profile.clan)
        return qs.none()

    @admin.action(description="Marcar como ejecutada en el juego")
    def mark_as_executed(self, request, queryset):
        from apps.clans.audit import log_audit_action

        for action in queryset:
            action.mark_executed()
            log_audit_action(
                user=request.user,
                clan=action.clan,
                action="EXECUTE_ROSTER_ACTION",
                source="admin",
                model_name="rosteraction",
                object_id=str(action.pk),
                object_repr=str(action),
                request=request,
            )

    @admin.action(description="Descartar acción")
    def mark_as_dismissed(self, request, queryset):
        from apps.clans.audit import log_audit_action

        for action in queryset:
            action.mark_dismissed()
            log_audit_action(
                user=request.user,
                clan=action.clan,
                action="DISMISS_ROSTER_ACTION",
                source="admin",
                model_name="rosteraction",
                object_id=str(action.pk),
                object_repr=str(action),
                request=request,
            )
