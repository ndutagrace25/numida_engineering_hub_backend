"""Generic, reusable string helpers. No feature-specific logic here."""


def is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def truncate(value, length, suffix="..."):
    if len(value) <= length:
        return value
    return value[: max(length - len(suffix), 0)] + suffix
