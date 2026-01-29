# config/settings.py
"""
Django settings for ClinicFlow project.
Production-ready for Render deployment.
"""

from datetime import timedelta
from pathlib import Path
import os
import sys

from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local .env (Render sets env vars automatically)
load_dotenv(BASE_DIR / ".env")

# =============================================================================
# SECURITY
# =============================================================================
# Support both naming conventions (Render uses SECRET_KEY, local might use DJANGO_SECRET_KEY)
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("DJANGO_SECRET_KEY") or "unsafe-dev-key-change-me"

# Default to False for production safety
_debug_val = os.getenv("DEBUG") or os.getenv("DJANGO_DEBUG") or "False"
DEBUG = _debug_val.lower() in ("true", "1", "yes")

# Print debug info at startup (visible in Render logs)
print(f"[SETTINGS] DEBUG={DEBUG}", file=sys.stderr)
print(f"[SETTINGS] SECRET_KEY set: {bool(os.getenv('SECRET_KEY') or os.getenv('DJANGO_SECRET_KEY'))}", file=sys.stderr)

# =============================================================================
# ALLOWED_HOSTS
# =============================================================================
# Render provides RENDER_EXTERNAL_HOSTNAME automatically
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()

# Base hosts for local development
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Add Render hostname if present (critical for production)
if render_hostname:
    ALLOWED_HOSTS.append(render_hostname)
    print(f"[SETTINGS] Added RENDER_EXTERNAL_HOSTNAME: {render_hostname}", file=sys.stderr)

# Add any extra hosts from environment (comma-separated)
extra_hosts = os.getenv("ALLOWED_HOSTS", "")
for host in extra_hosts.split(","):
    host = host.strip()
    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

print(f"[SETTINGS] ALLOWED_HOSTS={ALLOWED_HOSTS}", file=sys.stderr)

# =============================================================================
# CORS - Critical for frontend API calls
# =============================================================================
# Default local development origins
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Add production frontend URL(s) from environment
# MUST SET ON RENDER: CORS_ALLOWED_ORIGINS=https://frontend-4boy.onrender.com
cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
for origin in cors_env.split(","):
    origin = origin.strip()
    if origin and origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(origin)

print(f"[SETTINGS] CORS_ALLOWED_ORIGINS={CORS_ALLOWED_ORIGINS}", file=sys.stderr)

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Allow all standard headers including Authorization
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# =============================================================================
# CSRF - For admin and session-based auth
# =============================================================================
# Trusted origins for CSRF (needed for admin login in production)
CSRF_TRUSTED_ORIGINS = []

# Add Render backend URL for admin access
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_hostname}")

# Add from environment (comma-separated full URLs with https://)
csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS", "")
for origin in csrf_env.split(","):
    origin = origin.strip()
    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

print(f"[SETTINGS] CSRF_TRUSTED_ORIGINS={CSRF_TRUSTED_ORIGINS}", file=sys.stderr)

# =============================================================================
# INSTALLED APPS
# =============================================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    # Local apps
    "accounts",
    "patients",
    "visits",
    "prescriptions",
    "appointments",
]

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Must be after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # Must be before CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =============================================================================
# URL / WSGI
# =============================================================================
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# =============================================================================
# TEMPLATES
# =============================================================================
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

# =============================================================================
# DATABASE
# =============================================================================
# Uses DATABASE_URL if present (Render), otherwise SQLite (local dev)
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

print(f"[SETTINGS] DATABASE: {DATABASES['default'].get('ENGINE', 'unknown')}", file=sys.stderr)

# =============================================================================
# AUTH
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", _("English")),
    ("fr", _("French")),
]

USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]

# =============================================================================
# TIMEZONE
# =============================================================================
CLINIC_TIMEZONE = os.getenv("CLINIC_TIMEZONE", "Africa/Kinshasa")
TIME_ZONE = CLINIC_TIMEZONE

# =============================================================================
# STATIC FILES - WhiteNoise for production
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []

# =============================================================================
# FILE UPLOADS
# =============================================================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# =============================================================================
# STORAGES - Django 4.2+ unified configuration
# =============================================================================
# Cloudflare R2 settings (optional)
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "clinicflow")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")

# Use simpler static files storage that doesn't require manifest
# CompressedManifestStaticFilesStorage can fail if manifest is missing
if R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_ENDPOINT_URL:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": R2_ACCESS_KEY_ID,
                "secret_key": R2_SECRET_ACCESS_KEY,
                "bucket_name": R2_BUCKET_NAME,
                "endpoint_url": R2_ENDPOINT_URL,
                "default_acl": None,
                "file_overwrite": False,
                "region_name": "auto",
                "signature_version": "s3v4",
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    MEDIA_URL = f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/"
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            # Use CompressedStaticFilesStorage instead of CompressedManifestStaticFilesStorage
            # This avoids manifest errors when files are missing
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "config.pagination.FlexiblePageNumberPagination",
    "PAGE_SIZE": 10,
}

# =============================================================================
# SIMPLE JWT
# =============================================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# AFRICA'S TALKING SMS
# =============================================================================
AFRICASTALKING_USERNAME = os.getenv("AFRICASTALKING_USERNAME")
AFRICASTALKING_API_KEY = os.getenv("AFRICASTALKING_API_KEY")
AFRICASTALKING_SENDER_ID = os.getenv("AFRICASTALKING_SENDER_ID", "")

# =============================================================================
# LOGGING - Essential for debugging on Render
# =============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "stream": "ext://sys.stderr",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "appointments": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
