from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import RosterAction
from .serializers import RosterActionSerializer


class RosterActionViewSet(viewsets.ModelViewSet):
    """API endpoint to audit and manage proposed governance actions."""

    queryset = RosterAction.objects.all()
    serializer_class = RosterActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        clan_param = self.request.query_params.get("clan")
        if status_param:
            qs = qs.filter(status=status_param)
        if clan_param:
            qs = qs.filter(clan__tag=clan_param)
        return qs

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        """Mark the action as executed in the Clash Royale game by clan leadership."""
        roster_action = self.get_object()
        roster_action.mark_executed()
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
        return Response(
            {
                "message": f"Acción '{roster_action.get_action_type_display()}' descartada.",
                "action": RosterActionSerializer(roster_action).data,
            },
            status=status.HTTP_200_OK,
        )
