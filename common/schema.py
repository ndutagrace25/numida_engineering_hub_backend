"""Reusable OpenAPI documentation building blocks for drf-spectacular.

Nothing here affects runtime behavior — it only shapes what /api/schema/,
/api/docs/, and /api/redoc/ describe. The actual error envelope is produced
by common.exceptions.custom_exception_handler; ErrorResponseSerializer just
mirrors that shape for documentation purposes.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, inline_serializer
from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField(help_text="Machine-readable error code, e.g. VALIDATION_ERROR.")
    message = serializers.CharField(help_text="Human-readable summary of the error.")
    fields = serializers.DictField(
        help_text=(
            "Field-level validation errors, keyed by field name. Empty for non-validation errors."
        ),
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Shape of every error response: {"error": {"code", "message", "fields"}}."""

    error = ErrorDetailSerializer()


def _error_example(name, *, code, message, status_codes, fields=None):
    return OpenApiExample(
        name,
        value={"error": {"code": code, "message": message, "fields": fields or {}}},
        response_only=True,
        status_codes=status_codes,
    )


def validation_error_response(description, fields_example):
    """A 400 response documenting a VALIDATION_ERROR with realistic field errors."""
    return OpenApiResponse(
        response=ErrorResponseSerializer,
        description=description,
        examples=[
            _error_example(
                "ValidationError",
                code="VALIDATION_ERROR",
                message="Validation failed.",
                fields=fields_example,
                status_codes=["400"],
            )
        ],
    )


AUTHENTICATION_ERROR_RESPONSE = OpenApiResponse(
    response=ErrorResponseSerializer,
    description="Authentication credentials were not provided or are invalid.",
    examples=[
        _error_example(
            "NotAuthenticated",
            code="NOT_AUTHENTICATED",
            message="Authentication credentials were not provided.",
            status_codes=["401"],
        )
    ],
)


def permission_error_response(message):
    """A 403 response for actions restricted to a resource's owner/creator."""
    return OpenApiResponse(
        response=ErrorResponseSerializer,
        description="The authenticated user is not allowed to perform this action.",
        examples=[
            _error_example(
                "PermissionDenied",
                code="PERMISSION_DENIED",
                message=message,
                status_codes=["403"],
            )
        ],
    )


def not_found_response(resource_name):
    """A 404 response for a missing/inaccessible resource."""
    return OpenApiResponse(
        response=ErrorResponseSerializer,
        description=f"No {resource_name} exists with the given id.",
        examples=[
            _error_example(
                "NotFound",
                code="NOT_FOUND",
                message="Not found.",
                status_codes=["404"],
            )
        ],
    )


def success_envelope(name, data):
    """Wrap a serializer/field in the project's {"message", "data"} success
    envelope (see common.responses.success_response) for documentation.
    `data` may be a serializer instance, e.g. FooSerializer(many=True).
    """
    return inline_serializer(name=name, fields={"message": serializers.CharField(), "data": data})


def null_data_envelope(name):
    """The envelope shape for endpoints that respond with success_response(
    data=None, ...) — logout and every delete endpoint in this project —
    i.e. {"message": "...", "data": null}.
    """
    return success_envelope(name, serializers.JSONField(allow_null=True, default=None))
