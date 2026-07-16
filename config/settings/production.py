"""Production settings."""

from .base import *  # noqa: F403
from .base import LOGGING, env

DEBUG = False

ENVIRONMENT = "production"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# JSON-ready logs in production so log aggregators can parse them directly.
LOGGING["handlers"]["console"]["formatter"] = "json"
