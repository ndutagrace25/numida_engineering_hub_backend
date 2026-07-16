"""Settings used when running the test suite."""

from .base import *  # noqa: F403

DEBUG = False

ENVIRONMENT = "test"

# Django's test client uses "testserver" as the Host header.
ALLOWED_HOSTS = ["testserver"]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
