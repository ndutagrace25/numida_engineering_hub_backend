"""Generic, reusable field validators. No feature-specific logic here."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from common.utils.dates import is_in_future, is_monday
from common.utils.strings import is_blank
from common.utils.urls import is_https_url


def validate_https_url(value):
    if not is_https_url(value):
        raise ValidationError(_("URL must use HTTPS."), code="invalid_scheme")


def validate_future_week(value):
    if not is_in_future(value):
        raise ValidationError(_("Date must not be in the past."), code="not_future")


def validate_monday(value):
    if not is_monday(value):
        raise ValidationError(_("Date must fall on a Monday."), code="not_monday")


def validate_non_empty_string(value):
    if is_blank(value):
        raise ValidationError(_("This field must not be empty or blank."), code="blank")
