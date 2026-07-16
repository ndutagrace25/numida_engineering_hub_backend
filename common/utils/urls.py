"""Generic, reusable URL helpers. No feature-specific logic here."""

from urllib.parse import urlparse

from common.constants import SUPPORTED_URL_SCHEMES


def get_scheme(value):
    return urlparse(str(value)).scheme


def is_https_url(value):
    return get_scheme(value) in SUPPORTED_URL_SCHEMES
