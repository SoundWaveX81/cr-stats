from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clans.audit import log_audit_action

from .models import RosterAction
from .serializers import RosterActionSerializer


class RosterActionViewSet(viewsets.ModelViewSet):
    """API endpoint to audit and manage proposed governance actions."""

    queryset = RosterAction.objects.all()
    serializer_class = RosterActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                qs = qs.filter(clan=user.profile.clan)
            elif hasattr(user, "profile"):
                return qs.none()
        status_param = self.request.query_params.get("status")
        clan_param = self.request.query_params.get("clan")
        if status_param:
            qs = qs.filter(status=status_param)
        if clan_param:
            qs = qs.filter(clan__tag=clan_param)
        return qs

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = self.kwargs.get(lookup_url_kwarg)
        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                action_obj = RosterAction.objects.filter(pk=pk).first()
                if action_obj and action_obj.clan_id != user.profile.clan_id:
                    raise PermissionDenied("No tienes acceso a acciones de otro clan.")
            elif hasattr(user, "profile") and not user.profile.clan:
                raise PermissionDenied("No tienes un clan asignado.")
        return super().get_object()

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        """Mark the action as executed in the Clash Royale game by clan leadership."""
        roster_action = self.get_object()
        roster_action.mark_executed()
        log_audit_action(
            user=request.user,
            clan=roster_action.clan,
            action="EXECUTE_ROSTER_ACTION",
            source="api",
            model_name="RosterAction",
            object_id=str(roster_action.id),
            object_repr=str(roster_action),
            changes={
                "action_type": roster_action.action_type,
                "member": roster_action.member.tag,
                "reason": roster_action.reason,
            },
            request=request,
        )
        return Response(
            {
                "message": f"Acción '{roster_action.get_action_type_display()}' marcada como ejecutada.",
                "action": RosterActionSerializer(roster_action).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        """Dismiss the proposed disciplinary action."""
        roster_action = self.get_object()
        roster_action.mark_dismissed()
        log_audit_action(
            user=request.user,
            clan=roster_action.clan,
            action="DISMISS_ROSTER_ACTION",
            source="api",
            model_name="RosterAction",
            object_id=str(roster_action.id),
            object_repr=str(roster_action),
            changes={
                "action_type": roster_action.action_type,
                "member": roster_action.member.tag,
                "reason": roster_action.reason,
            },
            request=request,
        )
        return Response(
            {
                "message": f"Acción '{roster_action.get_action_type_display()}' descartada.",
                "action": RosterActionSerializer(roster_action).data,
            },
            status=status.HTTP_200_OK,
        )
