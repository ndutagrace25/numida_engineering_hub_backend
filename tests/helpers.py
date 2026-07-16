"""Assertions/helpers for the response envelopes defined in common/responses.py
and common/exceptions.py. Feature tests should use these instead of reaching
into raw response JSON directly, so the envelope shape only needs to change
in one place if it ever does.
"""


def get_data(response):
    return response.json()["data"]


def get_error(response):
    return response.json()["error"]
