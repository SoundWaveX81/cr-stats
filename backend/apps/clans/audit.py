from datetime import date, datetime, time
from typing import Any

from django.contrib.auth import get_user_model

from apps.clans.models import AuditLog, Clan

User = get_user_model()


def serialize_changes(data: dict[str, Any] | None) -> dict[str, Any]:
    """Sanitize and JSON-serialize form cleaned_data or change dictionaries."""
    if not data or not isinstance(data, dict):
        return {}
    safe = {}
    for k, v in data.items():
        if "password" in k.lower():
            continue
        if hasattr(v, "pk"):
            safe[k] = str(v)
        elif isinstance(v, (datetime, date, time)):
            safe[k] = v.isoformat()
        elif isinstance(v, (int, float, bool, str, list, dict)) or v is None:
            safe[k] = v
        else:
            safe[k] = str(v)
    return safe


def log_audit_action(
    user: Any = None,
    clan: Clan | None = None,
    action: str = "UPDATE",
    source: str = "api",
    model_name: str = "",
    object_id: str = "",
    object_repr: str = "",
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
    request: Any = None,
) -> AuditLog:
    """Helper to record an audit log entry for admin or API actions."""
    if request:
        if not user and getattr(request, "user", None) and request.user.is_authenticated:
            user = request.user
        if not ip_address:
            x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded:
                ip_address = x_forwarded.split(",")[0].strip()
            else:
                ip_address = request.META.get("REMOTE_ADDR")

    if user and not clan and hasattr(user, "profile") and user.profile.clan:
        clan = user.profile.clan

    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        clan=clan,
        action=action,
        source=source,
        model_name=model_name,
        object_id=str(object_id),
        object_repr=str(object_repr)[:255],
        changes=changes or {},
        ip_address=ip_address,
    )
