from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.bot.views import telegram_webhook_view
from apps.clans.views import ClanViewSet, MemberViewSet, WarPassViewSet
from apps.governance.views import RosterActionViewSet

from .views import health_check

router = DefaultRouter()
router.register(r"clans", ClanViewSet, basename="clan")
router.register(r"members", MemberViewSet, basename="member")
router.register(r"war-passes", WarPassViewSet, basename="war-pass")
router.register(r"roster-actions", RosterActionViewSet, basename="roster-action")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/bot/telegram/webhook/", telegram_webhook_view, name="telegram-webhook"),
    path("api/", include(router.urls)),
]
