"""Generic, reusable date helpers. No feature-specific logic here."""


def is_monday(value):
    return value.weekday() == 0
