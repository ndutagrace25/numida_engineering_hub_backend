"""Custom DRF exception handler producing one consistent error envelope:

{"error": {"code": "...", "message": "...", "fields": {}}}
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

SERVER_ERROR_CODE = "SERVER_ERROR"
DEFAULT_ERROR_CODE = "ERROR"

_ERROR_CODES_BY_STATUS = {
    400: "VALIDATION_ERROR",
    401: "NOT_AUTHENTICATED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def _as_str_list(value):
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _split_detail(detail):
    """Split DRF's exc.detail/response.data shape into (message, fields)."""
    if isinstance(detail, dict):
        if set(detail.keys()) == {"detail"}:
            return str(detail["detail"]), {}
        return "Validation failed.", {key: _as_str_list(value) for key, value in detail.items()}
    if isinstance(detail, list):
        return " ".join(str(item) for item in detail), {}
    return str(detail), {}


def custom_exception_handler(exc, context):
    # response is None for exceptions DRF doesn't recognize (unhandled server errors).
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.error("Unhandled exception while processing request", exc_info=exc)
        return Response(
            {
                "error": {
                    "code": SERVER_ERROR_CODE,
                    "message": "An unexpected error occurred.",
                    "fields": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    message, fields = _split_detail(response.data)
    code = _ERROR_CODES_BY_STATUS.get(response.status_code, DEFAULT_ERROR_CODE)

    if response.status_code >= 500:
        logger.error(message)
    elif response.status_code >= 400:
        logger.warning(message)

    response.data = {"error": {"code": code, "message": message, "fields": fields}}
    return response
