from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from apps.notifications.models import WarAlertPreference

from .audit import log_audit_action, serialize_changes
from .models import AuditLog, Clan, Member, UserProfile, WarPass

User = get_user_model()


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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.clan:
            return qs.filter(tag=request.user.profile.clan.tag)
        return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ("tag",)
        return ()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_audit_action(
            user=request.user,
            clan=obj,
            action="UPDATE" if change else "CREATE",
            source="admin",
            model_name="clan",
            object_id=obj.tag,
            object_repr=obj.name,
            changes=serialize_changes(form.cleaned_data),
            request=request,
        )


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("tag", "name", "clan", "role", "reliability_score", "is_active", "joined_at")
    list_filter = ("role", "is_active", "clan")
    search_fields = ("tag", "name", "clan__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.clan:
            return qs.filter(clan=request.user.profile.clan)
        return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(WarPass)
class WarPassAdmin(admin.ModelAdmin):
    list_display = ("member", "reason", "start_date", "end_date", "created_at")
    list_filter = ("start_date", "end_date", "member__clan")
    search_fields = ("member__name", "member__tag", "reason")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.clan:
            return qs.filter(member__clan=request.user.profile.clan)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if (
            not request.user.is_superuser
            and hasattr(request.user, "profile")
            and request.user.profile.clan
        ):
            if db_field.name == "member":
                kwargs["queryset"] = Member.objects.filter(
                    clan=request.user.profile.clan, is_active=True
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_audit_action(
            user=request.user,
            clan=obj.member.clan,
            action="UPDATE" if change else "CREATE",
            source="admin",
            model_name="warpass",
            object_id=str(obj.pk),
            object_repr=str(obj),
            changes=serialize_changes(form.cleaned_data),
            request=request,
        )

    def delete_model(self, request, obj):
        clan = obj.member.clan
        log_audit_action(
            user=request.user,
            clan=clan,
            action="DELETE",
            source="admin",
            model_name="warpass",
            object_id=str(obj.pk),
            object_repr=str(obj),
            request=request,
        )
        super().delete_model(request, obj)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "clan", "action", "source", "model_name", "object_repr")
    list_filter = ("action", "source", "created_at", "clan")
    search_fields = ("user__username", "clan__name", "object_repr", "model_name")
    readonly_fields = (
        "created_at",
        "user",
        "clan",
        "action",
        "source",
        "model_name",
        "object_id",
        "object_repr",
        "changes",
        "ip_address",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.clan:
            return qs.filter(clan=request.user.profile.clan)
        return qs.none()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = "user"
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if (
            not request.user.is_superuser
            and hasattr(request.user, "profile")
            and request.user.profile.clan
        ):
            if db_field.name == "clan":
                kwargs["queryset"] = Clan.objects.filter(tag=request.user.profile.clan.tag)
                kwargs["initial"] = request.user.profile.clan
            elif db_field.name == "player":
                kwargs["queryset"] = Member.objects.filter(clan=request.user.profile.clan)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    inlines = [UserProfileInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.clan:
            return qs.filter(profile__clan=request.user.profile.clan)
        return qs.none()

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser:
            fieldsets = (
                (None, {"fields": ("username", "password")}),
                ("Información Personal", {"fields": ("first_name", "last_name", "email")}),
                ("Permisos", {"fields": ("is_active",)}),
            )
        return fieldsets

    def has_delete_permission(self, request, obj=None):
        if obj and (obj.is_superuser or obj == request.user):
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if (
            not request.user.is_superuser
            and hasattr(request.user, "profile")
            and request.user.profile.clan
        ):
            profile, _ = UserProfile.objects.get_or_create(user=obj)
            if not profile.clan:
                profile.clan = request.user.profile.clan
                profile.save(update_fields=["clan"])

        target_clan = None
        if hasattr(obj, "profile") and obj.profile.clan:
            target_clan = obj.profile.clan
        elif hasattr(request.user, "profile") and request.user.profile.clan:
            target_clan = request.user.profile.clan

        log_audit_action(
            user=request.user,
            clan=target_clan,
            action="UPDATE" if change else "CREATE",
            source="admin",
            model_name="user",
            object_id=str(obj.pk),
            object_repr=obj.username,
            changes=serialize_changes(form.cleaned_data),
            request=request,
        )

    def delete_model(self, request, obj):
        target_clan = getattr(obj.profile, "clan", None) if hasattr(obj, "profile") else None
        log_audit_action(
            user=request.user,
            clan=target_clan,
            action="DELETE",
            source="admin",
            model_name="user",
            object_id=str(obj.pk),
            object_repr=obj.username,
            request=request,
        )
        super().delete_model(request, obj)
