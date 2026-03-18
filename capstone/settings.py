"""
Capstone Client — Django settings.

Single settings file. No base/dev/prod split.
Sam edits one file. Everything is Googleable.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.core",
    "apps.crm",
    "apps.jobs",
    "apps.billing",
    "apps.sync",
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

ROOT_URLCONF = "capstone.urls"

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

WSGI_APPLICATION = "capstone.wsgi.application"

# Database — PostgreSQL from env, SQLite fallback for quick start
_db_url = os.environ.get("DATABASE_URL", "")
if _db_url.startswith("postgresql://"):
    import re
    m = re.match(
        r"postgresql://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<name>.+)",
        _db_url,
    )
    if m:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": m.group("name"),
                "USER": m.group("user"),
                "PASSWORD": m.group("password"),
                "HOST": m.group("host"),
                "PORT": m.group("port") or "5432",
            }
        }
    else:
        raise ValueError(f"Cannot parse DATABASE_URL: {_db_url}")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "/oauth2/login"
LOGIN_REDIRECT_URL = "/admin/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Microsoft Entra ID (Azure AD) authentication
_azure_tenant_id = os.environ.get("AZURE_TENANT_ID", "")
_azure_client_id = os.environ.get("AZURE_CLIENT_ID", "")

if _azure_client_id:
    INSTALLED_APPS.append("django_auth_adfs")
    AUTHENTICATION_BACKENDS = [
        "django_auth_adfs.backend.AdfsAuthCodeBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]
    AUTH_ADFS = {
        "AUDIENCE": _azure_client_id,
        "CLIENT_ID": _azure_client_id,
        "CLIENT_SECRET": os.environ.get("AZURE_CLIENT_SECRET", ""),
        "TENANT_ID": _azure_tenant_id,
        "RELYING_PARTY_ID": _azure_client_id,
        "LOGIN_EXEMPT_URLS": [
            "^sync/inbound/$",
            "^admin/login/$",
        ],
    }
else:
    # Fall back to admin login when Entra is not configured
    LOGIN_URL = "/admin/login/"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "apps.sync": {"handlers": ["console"], "level": "INFO"},
    },
}
