"""Direct unit tests for common.exceptions.custom_exception_handler — the
shared handler that shapes every error response in the API. Most of its
branches are already exercised indirectly through view-level error-format
assertions across the apps; this file specifically covers the unhandled
server-error (500) path, which nothing else in the suite deliberately
triggers.
"""

from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from common.exceptions import custom_exception_handler


class CustomExceptionHandlerTests(TestCase):
    def test_unhandled_exception_returns_standard_500_envelope(self):
        response = custom_exception_handler(ValueError("boom"), context={})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.data,
            {
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "fields": {},
                }
            },
        )

    def test_not_found_uses_standard_error_code(self):
        response = custom_exception_handler(NotFound(), context={})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "NOT_FOUND")
        self.assertEqual(response.data["error"]["fields"], {})

    def test_field_validation_error_splits_message_and_fields(self):
        response = custom_exception_handler(
            ValidationError({"email": ["This field is required."]}), context={}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(response.data["error"]["fields"], {"email": ["This field is required."]})
        self.assertEqual(response.data["error"]["message"], "Validation failed.")
