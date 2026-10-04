import sys
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env from backend/ or project root
env = environ.Env(
    DEBUG=(bool, True),
    TESTING=(bool, "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)),
)

env_file = BASE_DIR / ".env"
root_env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)
elif root_env_file.exists():
    environ.Env.read_env(root_env_file)

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-dev-cr-total-2026-replace-in-production",
)

DEBUG = env.bool("DEBUG", default=True)
TESTING = env.bool(
    "TESTING", default=("pytest" in sys.modules or any("pytest" in arg for arg in sys.argv))
)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "web", "api", "*"])

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    # Domain apps
    "apps.clans",
    "apps.wars",
    "apps.governance",
    "apps.notifications",
    "apps.ingestion",
    "apps.bot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
# If testing, default to SQLite in-memory for fast and hermetic unit test execution
if TESTING:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    default_db_url = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    DATABASES = {
        "default": env.db("DATABASE_URL", default=default_db_url),
    }

# Cache
redis_url = env("REDIS_URL", default="")
if redis_url and not TESTING:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": redis_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-cr-total-locmem",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "COERCE_DECIMAL_TO_STRING": False,
}

# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

if TESTING:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

CELERY_BEAT_SCHEDULE = {
    "sync-clan-data-hourly": {
        "task": "apps.ingestion.tasks.task_sync_clan_data",
        "schedule": crontab(minute=0),
    },
    "send-pending-attack-reminders-hourly": {
        "task": "apps.ingestion.tasks.task_send_pending_attack_reminders",
        "schedule": crontab(minute=0, hour="6,7,8,9,10", day_of_week="4,5,6,0"),
    },
    "evaluate-war-day-governance-daily": {
        "task": "apps.governance.tasks.task_evaluate_war_day_governance",
        "schedule": crontab(hour=10, minute=5),
    },
}

# Supercell Clash Royale API Settings
CLASH_ROYALE_API_KEY = env("API_KEY", default=env("CLASH_ROYALE_API_KEY", default=""))
CLASH_ROYALE_BASE_URL = env("CLASH_ROYALE_BASE_URL", default="https://api.clashroyale.com/v1")

# Telegram & Discord Bot Configuration
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_SECRET_TOKEN = env("TELEGRAM_BOT_SECRET_TOKEN", default="")
DISCORD_BOT_TOKEN = env("DISCORD_BOT_TOKEN", default="")
DEFAULT_TELEGRAM_CHAT_ID = env(
    "DEFAULT_TELEGRAM_CHAT_ID", default=env("TELEGRAM_CHAT_ID", default="")
)
DEFAULT_DISCORD_WEBHOOK_URL = env(
    "DEFAULT_DISCORD_WEBHOOK_URL", default=env("DISCORD_WEBHOOK_URL", default="")
)
