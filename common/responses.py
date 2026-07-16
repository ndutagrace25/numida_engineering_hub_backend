"""Reusable response helpers producing one consistent success envelope:

{"message": "...", "data": {...}}

Feature-specific response shaping does not belong here — only the envelope.
"""

from rest_framework import status
from rest_framework.response import Response


def success_response(
    data=None, message="Request completed successfully.", status_code=status.HTTP_200_OK
):
    return Response(
        {"message": message, "data": data if data is not None else {}}, status=status_code
    )


def created_response(data=None, message="Resource created successfully."):
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
