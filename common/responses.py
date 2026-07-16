"""Reusable response helpers producing one consistent success envelope:

{"message": "...", "data": {...}}

Feature-specific response shaping does not belong here — only the envelope.
"""

from rest_framework import status
from rest_framework.response import Response

# Distinguishes "caller passed no data" (-> {}) from "caller explicitly wants
# null data" (data=None -> JSON null); both would otherwise look identical
# with a plain default of None.
_UNSET = object()


def success_response(
    data=_UNSET, message="Request completed successfully.", status_code=status.HTTP_200_OK
):
    if data is _UNSET:
        data = {}
    return Response({"message": message, "data": data}, status=status_code)


def created_response(data=_UNSET, message="Resource created successfully."):
    return success_response(data=data, message=message, status_code=status.HTTP_201_CREATED)


def deleted_response(message="Resource deleted successfully."):
    return success_response(data={}, message=message, status_code=status.HTTP_200_OK)


def paginated_response(
    *, count, next_url, previous_url, results, message="Request completed successfully."
):
    data = {
        "count": count,
        "next": next_url,
        "previous": previous_url,
        "results": results,
    }
    return success_response(data=data, message=message, status_code=status.HTTP_200_OK)
