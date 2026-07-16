"""Generic, reusable date helpers. No feature-specific logic here."""

from django.utils import timezone


def today():
    return timezone.localdate()


def is_monday(value):
    return value.weekday() == 0


def is_in_future(value):
    return value >= today()
