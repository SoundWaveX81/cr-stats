from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse


def health_check(request) -> JsonResponse:
    """Check database and cache service availability."""
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    cache_ok = True
    try:
        cache.set("healthcheck", "ok", 5)
        cache_ok = cache.get("healthcheck") == "ok"
    except Exception:
        cache_ok = False

    status_code = 200 if (db_ok and cache_ok) else 503
    return JsonResponse(
        {
            "status": "ok" if status_code == 200 else "degraded",
            "database": db_ok,
            "cache": cache_ok,
        },
        status=status_code,
    )
