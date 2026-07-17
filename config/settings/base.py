"""
Base Django settings for the Numida Engineering Hub project.

Shared by every environment. Environment-specific settings modules
(development, test, production) import from this module and override
only what differs for that environment.
"""

from pathlib import Path

import environ

from common.constants import API_VERSION

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-env")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Overridden explicitly by each concrete settings module (development/test/production).
ENVIRONMENT = "development"


# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.standups",
    "apps.presence",
    "apps.aob",
    "apps.pto",
    "apps.pull_requests",
    "apps.dashboard",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "common.middleware.RequestLoggingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
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
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://postgres:postgres@localhost:5432/numida_engineering_hub",
    ),
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Nairobi"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework
# https://www.django-rest-framework.org/api-guide/settings/

REST_FRAMEWORK = {
    # NonPromptingBasicAuthentication first: it advertises a WWW-Authenticate
    # challenge, so unauthenticated requests get 401 rather than being
    # coerced to 403 (DRF falls back to 403 if the *first* authenticator
    # can't challenge) — same reasoning as plain BasicAuthentication, but
    # its header value doesn't trigger a browser's native login popup on
    # the frontend's own XHR/fetch calls (see common/authentication.py).
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "common.authentication.NonPromptingBasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
}


# drf-spectacular (OpenAPI schema generation)
# https://drf-spectacular.readthedocs.io/en/latest/settings.html

SPECTACULAR_SETTINGS = {
    "TITLE": "Numida Engineering Hub API",
    "DESCRIPTION": "REST API powering the Numida Engineering Hub.",
    "VERSION": API_VERSION,
    "CONTACT": {"name": "Engineering Team"},
    "LICENSE": {"name": "MIT"},
    # The schema itself is served at /api/schema/, so it has no business
    # linking to a copy of itself.
    "SERVE_INCLUDE_SCHEMA": False,
    # Every view is under /api/v1/ (except the schema/docs endpoints
    # themselves) — stripping it keeps operation IDs and tag inference
    # focused on the resource path instead of repeating "v1" everywhere.
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "TAGS": [
        {"name": "Authentication", "description": "Session login, logout, and the current user."},
        {"name": "Users", "description": "Read-only directory of active users."},
        {"name": "Standups", "description": "Daily standup submissions and their nested items."},
        {"name": "Presence", "description": "Online/recently-active/offline presence tracking."},
        {"name": "AOB", "description": "Any-other-business items raised for a given week."},
        {"name": "PTO", "description": "Paid time off entries."},
        {"name": "Pull Request Links", "description": "Pull requests shared for a given week."},
        {"name": "Dashboard", "description": "Aggregated read-only view across all modules."},
    ],
    "SWAGGER_UI_SETTINGS": {
        "displayRequestDuration": True,
        "persistAuthorization": True,
        "defaultModelsExpandDepth": 1,
        "docExpansion": "none",
        "tryItOutEnabled": True,
    },
    "REDOC_UI_SETTINGS": {
        "hideDownloadButton": False,
        "expandResponses": "200,201",
    },
}


# django-cors-headers
# https://github.com/adamchainz/django-cors-headers

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# The frontend authenticates with session cookies sent cross-origin
# (different port = different origin), so both credentialed CORS and CSRF
# need the frontend's origin explicitly trusted:
# - Without CORS_ALLOW_CREDENTIALS, browsers reject any fetch/XHR made with
#   `withCredentials: true` regardless of what CORS_ALLOWED_ORIGINS says.
# - Without CSRF_TRUSTED_ORIGINS, Django's CSRF Origin check rejects
#   state-changing requests (e.g. logout) from an authenticated session,
#   since the request's Origin header won't match the backend's own host.
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


# Logging
# https://docs.djangoproject.com/en/5.2/topics/logging/
#
# Console formatter is human-readable for local development; production
# switches the "console" handler to the JSON formatter (see production.py).
# Only method/path/status/duration are ever logged for requests — never
# headers, cookies, or bodies — so secrets can't leak through logs.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
        "json": {
            "()": "common.logging.JSONFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
