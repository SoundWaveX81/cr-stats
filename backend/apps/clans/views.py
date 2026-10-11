from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.ingestion.services import SyncClanService, SyncRiverRaceService
from apps.wars.services import CurrentWarService, MemberWarHistoryService

from .audit import log_audit_action
from .models import Clan, Member, WarPass
from .serializers import (
    ClanSerializer,
    CustomTokenObtainPairSerializer,
    MemberSerializer,
    WarPassSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT login endpoint that provides user profile and clan details."""

    serializer_class = CustomTokenObtainPairSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Retrieve current authenticated user's profile, role, clan, and player association."""
    user = request.user
    profile = getattr(user, "profile", None)
    data = {
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
    return Response(data, status=status.HTTP_200_OK)


class ClanViewSet(viewsets.ModelViewSet):
    """API endpoint to view and manage registered Clash Royale clans."""

    queryset = Clan.objects.all()
    serializer_class = ClanSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_value_regex = r"[^/]+"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                return qs.filter(tag=user.profile.clan.tag)
            elif hasattr(user, "profile"):
                return qs.none()
        return qs

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        val = self.kwargs.get(lookup_url_kwarg)
        if val and not val.startswith("#"):
            val = f"#{val}"
            self.kwargs[lookup_url_kwarg] = val

        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                if val and val != user.profile.clan.tag:
                    raise PermissionDenied("No tienes acceso a este clan.")
            elif hasattr(user, "profile") and not user.profile.clan:
                raise PermissionDenied("No tienes un clan asignado.")

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
            log_audit_action(
                user=request.user,
                clan=clan,
                action="SYNC_CLAN",
                source="api",
                model_name="Clan",
                object_id=clan.tag,
                object_repr=str(clan),
                changes={"sync_type": "current_race_and_clan"},
                request=request,
            )
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
            log_audit_action(
                user=request.user,
                clan=clan,
                action="SYNC_CLAN",
                source="api",
                model_name="Clan",
                object_id=clan.tag,
                object_repr=str(clan),
                changes={"sync_type": "river_race_history", "count": count},
                request=request,
            )
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
        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                qs = qs.filter(member__clan=user.profile.clan)
            elif hasattr(user, "profile"):
                return qs.none()
        clan_param = self.request.query_params.get("clan")
        member_param = self.request.query_params.get("member")
        if clan_param:
            qs = qs.filter(member__clan__tag=clan_param)
        if member_param:
            qs = qs.filter(member__tag=member_param)
        return qs

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = self.kwargs.get(lookup_url_kwarg)
        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                pass_obj = WarPass.objects.filter(pk=pk).first()
                if pass_obj and pass_obj.member.clan_id != user.profile.clan_id:
                    raise PermissionDenied("No tienes acceso a este pase de guerra.")
            elif hasattr(user, "profile") and not user.profile.clan:
                raise PermissionDenied("No tienes un clan asignado.")
        return super().get_object()

    def perform_create(self, serializer):
        user = self.request.user
        member = serializer.validated_data.get("member")
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                if member.clan != user.profile.clan:
                    raise PermissionDenied(
                        "No puedes otorgar un pase de guerra a un miembro de otro clan."
                    )
            elif hasattr(user, "profile") and not user.profile.clan:
                raise PermissionDenied("No tienes un clan asignado.")
        pass_instance = serializer.save()
        log_audit_action(
            user=user,
            clan=member.clan,
            action="CREATE_WAR_PASS",
            source="api",
            model_name="WarPass",
            object_id=str(pass_instance.id),
            object_repr=str(pass_instance),
            changes={
                "member": member.tag,
                "reason": pass_instance.reason,
                "start_date": str(pass_instance.start_date),
                "end_date": str(pass_instance.end_date),
            },
            request=self.request,
        )

    def perform_destroy(self, instance):
        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                if instance.member.clan != user.profile.clan:
                    raise PermissionDenied("No puedes revocar un pase de guerra de otro clan.")
            elif hasattr(user, "profile") and not user.profile.clan:
                raise PermissionDenied("No tienes un clan asignado.")
        log_audit_action(
            user=user,
            clan=instance.member.clan,
            action="DELETE_WAR_PASS",
            source="api",
            model_name="WarPass",
            object_id=str(instance.id),
            object_repr=str(instance),
            changes={
                "member": instance.member.tag,
                "reason": instance.reason,
            },
            request=self.request,
        )
        instance.delete()


class MemberViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint to view member details and historical war attendance."""

    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_value_regex = r"[^/]+"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                qs = qs.filter(clan=user.profile.clan)
            elif hasattr(user, "profile"):
                return qs.none()
        return qs

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        val = self.kwargs.get(lookup_url_kwarg)
        if val and not val.startswith("#"):
            val = f"#{val}"
            self.kwargs[lookup_url_kwarg] = val

        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            if hasattr(user, "profile") and user.profile.clan:
                member = Member.objects.filter(tag=val).first()
                if member and member.clan_id != user.profile.clan_id:
                    raise PermissionDenied("No tienes acceso a este miembro.")
            elif hasattr(user, "profile") and not user.profile.clan:
                raise PermissionDenied("No tienes un clan asignado.")

        return super().get_object()

    @action(detail=True, methods=["get"], url_path="war-history")
    def war_history(self, request, pk=None):
        """Retrieve war attack history across the last 10 river races for this member."""
        member = self.get_object()
        service = MemberWarHistoryService()
        data = service.get_member_war_history(member)
        return Response(data, status=status.HTTP_200_OK)
