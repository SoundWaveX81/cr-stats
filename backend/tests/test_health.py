import pytest
from django.conf import settings
from django.urls import reverse

from config.celery import app as celery_app


@pytest.mark.django_db
def test_health_check_endpoint(api_client):
    """Test health check returns 200 OK and reports services status."""
    url = reverse("health-check")
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] is True
    assert data["cache"] is True


def test_django_core_settings():
    """Verify essential Django settings are properly loaded."""
    assert settings.SECRET_KEY != ""
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "rest_framework_simplejwt" in settings.INSTALLED_APPS
    assert settings.ROOT_URLCONF == "config.urls"


def test_celery_app_initialized():
    """Verify Celery app initialization and naming."""
    assert celery_app.main == "cr_total"
    assert celery_app.conf.timezone == "UTC"


@pytest.mark.django_db
def test_init_admin_command():
    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    User = get_user_model()
    call_command("init_admin", username="testadmin", password="password123")

    user = User.objects.filter(username="testadmin").first()
    assert user is not None
    assert user.is_superuser is True
    assert user.is_staff is True
