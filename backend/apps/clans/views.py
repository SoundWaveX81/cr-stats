from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.ingestion.services import SyncClanService, SyncRiverRaceService
from apps.wars.services import CurrentWarService

from .models import Clan, WarPass
from .serializers import ClanSerializer, MemberSerializer, WarPassSerializer


class ClanViewSet(viewsets.ModelViewSet):
    """API endpoint to view and manage registered Clash Royale clans."""

    queryset = Clan.objects.all()
    serializer_class = ClanSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_value_regex = r"[^/]+"

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        val = self.kwargs.get(lookup_url_kwarg)
        if val and not val.startswith("#"):
            self.kwargs[lookup_url_kwarg] = f"#{val}"
        return super().get_object()

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """Retrieve the roster of members for this clan."""
        clan = self.get_object()
        members = clan.members.filter(is_active=True).order_by("-reliability_score")
        serializer = MemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="current-war")
    def current_war(self, request, pk=None):
        """Retrieve live River Race standings, participant attacks, and projected scores."""
        clan = self.get_object()
        service = CurrentWarService()
        data = service.get_war_overview(clan)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def sync(self, request, pk=None):
        """Trigger an on-demand synchronization with the official Clash Royale API."""
        clan = self.get_object()
        try:
            sync_clan_service = SyncClanService()
            sync_clan_service.sync(clan)

            sync_race_service = SyncRiverRaceService()
            sync_race_service.sync(clan)
            if request.data.get("include_history") or request.query_params.get("include_history"):
                sync_race_service.sync_race_history(clan)

            clan.refresh_from_db()
            return Response(
                {
                    "message": "Sincronización completada con éxito.",
                    "clan": ClanSerializer(clan).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {"error": f"Error durante la sincronización: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="sync-history",
        permission_classes=[IsAuthenticated],
    )
    def sync_history(self, request, pk=None):
        """Trigger ingestion of past completed river races from /riverracelog."""
        clan = self.get_object()
        try:
            sync_race_service = SyncRiverRaceService()
            count = sync_race_service.sync_race_history(clan)
            return Response(
                {"message": f"Historial de {count} carreras fluviales sincronizado con éxito."},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {"error": f"Error al sincronizar historial: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class WarPassViewSet(viewsets.ModelViewSet):
    """API endpoint to manage War Passes for excused absences."""

    queryset = WarPass.objects.all()
    serializer_class = WarPassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        clan_param = self.request.query_params.get("clan")
        member_param = self.request.query_params.get("member")
        if clan_param:
            qs = qs.filter(member__clan__tag=clan_param)
        if member_param:
            qs = qs.filter(member__tag=member_param)
        return qs
