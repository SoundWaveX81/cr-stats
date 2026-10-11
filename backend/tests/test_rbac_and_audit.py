from datetime import date, timedelta

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.clans.admin import (
    AuditLogAdmin,
    ClanAdmin,
    CustomUserAdmin,
    MemberAdmin,
    WarPassAdmin,
)
from apps.clans.models import AuditLog, Clan, Member, UserProfile, WarPass
from apps.governance.models import RosterAction
from apps.notifications.admin import (
    NotificationChannelAdmin,
    WarAlertPreferenceAdmin,
)
from apps.notifications.models import NotificationChannel, WarAlertPreference

User = get_user_model()


@pytest.fixture
def clan1(db):
    return Clan.objects.create(tag="#CLAN1", name="Clan Uno")


@pytest.fixture
def clan2(db):
    return Clan.objects.create(tag="#CLAN2", name="Clan Dos")


@pytest.fixture
def member1(clan1):
    return Member.objects.create(clan=clan1, tag="#P1", name="Player One", role="member")


@pytest.fixture
def member2(clan2):
    return Member.objects.create(clan=clan2, tag="#P2", name="Player Two", role="member")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="superadmin", email="admin@example.com", password="adminpassword123"
    )


@pytest.fixture
def clan_admin_user(clan1, member1):
    user = User.objects.create_user(
        username="clan1_admin", email="admin1@example.com", password="clanpassword123"
    )
    user.refresh_from_db()
    return user


@pytest.fixture
def clan_member_user(clan1, member1):
    user = User.objects.create_user(
        username="clan1_member", email="member1@example.com", password="clanpassword123"
    )
    UserProfile.objects.create(user=user, clan=clan1, role="member", player=member1)
    user.refresh_from_db()
    return user


@pytest.mark.django_db
class TestUserProfileAndRoleSync:
    def test_role_clan_admin_sets_is_staff(self, clan1):
        user = User.objects.create_user(username="test_admin", password="password123")
        assert not user.is_staff
        profile = UserProfile.objects.create(user=user, clan=clan1, role="clan_admin")
        user.refresh_from_db()
        assert user.is_staff is True

        # Demote to member
        profile.role = "member"
        profile.save()
        user.refresh_from_db()
        assert user.is_staff is False

    def test_superuser_retains_staff_status(self, superuser, clan1):
        assert superuser.is_staff is True
        superuser.refresh_from_db()
        assert superuser.is_staff is True


@pytest.mark.django_db
class TestAuthAndMeEndpoint:
    def test_login_returns_token_and_profile_claims(self, clan_admin_user, clan1):
        client = APIClient()
        response = client.post(
            "/api/token/",
            {"username": "clan1_admin", "password": "clanpassword123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "access" in data
        assert "refresh" in data
        assert "user" in data
        assert data["user"]["username"] == "clan1_admin"
        assert data["user"]["clan_tag"] == clan1.tag
        assert data["user"]["role"] == "clan_admin"
        assert data["user"]["player_tag"] == "#P1"

        # Inspect token payload
        token = AccessToken(data["access"])
        assert token["clan_tag"] == clan1.tag
        assert token["role"] == "clan_admin"
        assert token["player_tag"] == "#P1"

    def test_me_endpoint_for_clan_admin(self, clan_admin_user, clan1):
        client = APIClient()
        client.force_authenticate(user=clan_admin_user)
        response = client.get("/api/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "clan1_admin"
        assert response.data["clan_tag"] == clan1.tag
        assert response.data["role"] == "clan_admin"
        assert response.data["player_tag"] == "#P1"
        assert response.data["is_superuser"] is False

    def test_me_endpoint_for_superuser(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        response = client.get("/api/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "superadmin"
        assert response.data["is_superuser"] is True
        assert response.data["clan_tag"] is None


@pytest.mark.django_db
class TestClanIsolationEndpoints:
    def test_clan_viewset_isolation(self, clan1, clan2, clan_member_user, superuser):
        member_client = APIClient()
        member_client.force_authenticate(user=clan_member_user)

        # Listing clans returns only clan1
        res = member_client.get("/api/clans/")
        assert res.status_code == status.HTTP_200_OK
        tags = [c["tag"] for c in res.data]
        assert tags == [clan1.tag]

        # Accessing own clan
        res_own = member_client.get(f"/api/clans/{clan1.tag.replace('#', '%23')}/")
        assert res_own.status_code == status.HTTP_200_OK

        # Accessing other clan returns 403 Forbidden
        res_other = member_client.get(f"/api/clans/{clan2.tag.replace('#', '%23')}/")
        assert res_other.status_code == status.HTTP_403_FORBIDDEN

        # Accessing other clan members returns 403 Forbidden
        res_other_members = member_client.get(
            f"/api/clans/{clan2.tag.replace('#', '%23')}/members/"
        )
        assert res_other_members.status_code == status.HTTP_403_FORBIDDEN

        # Superuser can access both
        super_client = APIClient()
        super_client.force_authenticate(user=superuser)
        res_super_list = super_client.get("/api/clans/")
        assert len(res_super_list.data) == 2
        res_super_clan2 = super_client.get(f"/api/clans/{clan2.tag.replace('#', '%23')}/")
        assert res_super_clan2.status_code == status.HTTP_200_OK

    def test_member_viewset_isolation(self, member1, member2, clan_member_user):
        client = APIClient()
        client.force_authenticate(user=clan_member_user)

        # Listing returns only member1
        res = client.get("/api/members/")
        assert res.status_code == status.HTTP_200_OK
        tags = [m["tag"] for m in res.data]
        assert tags == [member1.tag]

        # Member 2 war history returns 403
        res_other = client.get(f"/api/members/{member2.tag.replace('#', '%23')}/war-history/")
        assert res_other.status_code == status.HTTP_403_FORBIDDEN

    def test_war_pass_isolation_and_audit(self, member1, member2, clan_admin_user):
        client = APIClient()
        client.force_authenticate(user=clan_admin_user)

        # Create pass for member of own clan
        start = str(date.today())
        end = str(date.today() + timedelta(days=3))
        res_create = client.post(
            "/api/war-passes/",
            {
                "member": member1.tag,
                "reason": "Examen de universidad",
                "start_date": start,
                "end_date": end,
            },
            format="json",
        )
        assert res_create.status_code == status.HTTP_201_CREATED
        pass_id = res_create.data["id"]

        # AuditLog should have registered CREATE_WAR_PASS
        audit_entry = AuditLog.objects.filter(
            action="CREATE_WAR_PASS", object_id=str(pass_id)
        ).first()
        assert audit_entry is not None
        assert audit_entry.user == clan_admin_user
        assert audit_entry.clan == member1.clan
        assert audit_entry.source == "api"

        # Attempt to create pass for member of foreign clan returns 403
        res_forbidden = client.post(
            "/api/war-passes/",
            {
                "member": member2.tag,
                "reason": "Viaje",
                "start_date": start,
                "end_date": end,
            },
            format="json",
        )
        assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

        # Delete own war pass
        res_del = client.delete(f"/api/war-passes/{pass_id}/")
        assert res_del.status_code == status.HTTP_204_NO_CONTENT

        # AuditLog should have registered DELETE_WAR_PASS
        del_audit = AuditLog.objects.filter(
            action="DELETE_WAR_PASS", object_id=str(pass_id)
        ).first()
        assert del_audit is not None
        assert del_audit.user == clan_admin_user

    def test_roster_action_isolation_and_audit(
        self, clan1, clan2, member1, member2, clan_admin_user
    ):
        act1 = RosterAction.objects.create(
            clan=clan1, member=member1, action_type="kick", reason="Inactivo"
        )
        act2 = RosterAction.objects.create(
            clan=clan2, member=member2, action_type="kick", reason="Inactivo clan 2"
        )

        client = APIClient()
        client.force_authenticate(user=clan_admin_user)

        # Listing only includes clan1
        res = client.get("/api/roster-actions/")
        assert res.status_code == status.HTTP_200_OK
        ids = [a["id"] for a in res.data]
        assert ids == [act1.id]

        # Executing foreign clan action returns 403
        res_forbid = client.post(f"/api/roster-actions/{act2.id}/execute/")
        assert res_forbid.status_code == status.HTTP_403_FORBIDDEN

        # Executing own action succeeds and creates AuditLog
        res_exec = client.post(f"/api/roster-actions/{act1.id}/execute/")
        assert res_exec.status_code == status.HTTP_200_OK
        act1.refresh_from_db()
        assert act1.status == "executed"

        audit = AuditLog.objects.filter(
            action="EXECUTE_ROSTER_ACTION", object_id=str(act1.id)
        ).first()
        assert audit is not None
        assert audit.user == clan_admin_user
        assert audit.clan == clan1


@pytest.mark.django_db
class TestDjangoAdminMultiTenancyScoping:
    def test_clan_admin_scoping_in_admin_views(
        self, clan1, clan2, member1, member2, clan_admin_user, superuser
    ):
        site = AdminSite()
        clan_admin = ClanAdmin(Clan, site)
        member_admin = MemberAdmin(Member, site)
        warpass_admin = WarPassAdmin(WarPass, site)
        audit_admin = AuditLogAdmin(AuditLog, site)
        channel_admin = NotificationChannelAdmin(NotificationChannel, site)
        pref_admin = WarAlertPreferenceAdmin(WarAlertPreference, site)
        user_admin = CustomUserAdmin(User, site)

        rf = RequestFactory()
        req_clan_admin = rf.get("/admin/")
        req_clan_admin.user = clan_admin_user

        req_super = rf.get("/admin/")
        req_super.user = superuser

        # Clan querysets
        assert set(clan_admin.get_queryset(req_clan_admin)) == {clan1}
        assert set(clan_admin.get_queryset(req_super)) == {clan1, clan2}
        assert clan_admin.has_add_permission(req_clan_admin) is False
        assert clan_admin.has_delete_permission(req_clan_admin) is False
        assert clan_admin.has_add_permission(req_super) is True

        # Member querysets
        assert set(member_admin.get_queryset(req_clan_admin)) == {member1}
        assert set(member_admin.get_queryset(req_super)) == {member1, member2}

        # WarPass querysets
        p1 = WarPass.objects.create(
            member=member1, reason="Test 1", start_date=date.today(), end_date=date.today()
        )
        p2 = WarPass.objects.create(
            member=member2, reason="Test 2", start_date=date.today(), end_date=date.today()
        )
        assert set(warpass_admin.get_queryset(req_clan_admin)) == {p1}
        assert set(warpass_admin.get_queryset(req_super)) == {p1, p2}

        # AuditLog querysets
        a1 = AuditLog.objects.create(clan=clan1, action="TEST", model_name="test")
        a2 = AuditLog.objects.create(clan=clan2, action="TEST", model_name="test")
        assert set(audit_admin.get_queryset(req_clan_admin)) == {a1}
        assert set(audit_admin.get_queryset(req_super)) == {a1, a2}
        assert audit_admin.has_add_permission(req_clan_admin) is False
        assert audit_admin.has_change_permission(req_clan_admin) is False
        assert audit_admin.has_delete_permission(req_clan_admin) is False

        # Channel & Preferences
        ch1 = NotificationChannel.objects.create(clan=clan1, provider="console", config={})
        ch2 = NotificationChannel.objects.create(clan=clan2, provider="console", config={})
        assert set(channel_admin.get_queryset(req_clan_admin)) == {ch1}
        assert set(channel_admin.get_queryset(req_super)) == {ch1, ch2}

        pref1, _ = WarAlertPreference.objects.get_or_create(clan=clan1)
        pref2, _ = WarAlertPreference.objects.get_or_create(clan=clan2)
        assert set(pref_admin.get_queryset(req_clan_admin)) == {pref1}
        assert set(pref_admin.get_queryset(req_super)) == {pref1, pref2}

        # User admin scoping
        assert set(user_admin.get_queryset(req_clan_admin)) == {clan_admin_user}
        assert superuser in set(user_admin.get_queryset(req_super))
