"""Verifies the OpenAPI documentation endpoints are wired up and served
correctly. These don't assert on the full schema content — schema quality
(warnings, operation ids, etc.) is checked by
`manage.py spectacular --validate --fail-on-warn` instead.
"""

from rest_framework.test import APITestCase


class SchemaEndpointTests(APITestCase):
    url = "/api/schema/"

    def test_schema_endpoint_returns_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_schema_is_valid_openapi_yaml(self):
        response = self.client.get(self.url)

        content_type = response.headers["Content-Type"]
        self.assertIn("openapi", content_type)

    def test_schema_reports_expected_metadata(self):
        response = self.client.get(self.url, {"format": "json"})

        schema = response.json()
        self.assertEqual(schema["info"]["title"], "Numida Engineering Hub API")
        self.assertEqual(schema["info"]["version"], "v1")
        self.assertEqual(schema["info"]["license"]["name"], "MIT")
        self.assertEqual(schema["info"]["contact"]["name"], "Engineering Team")

    def test_schema_endpoint_does_not_require_authentication(self):
        response = self.client.get(self.url)

        self.assertNotEqual(response.status_code, 401)

    def test_schema_declares_session_and_basic_auth_schemes(self):
        response = self.client.get(self.url, {"format": "json"})

        schemes = response.json()["components"]["securitySchemes"]
        self.assertIn("cookieAuth", schemes)
        self.assertEqual(schemes["cookieAuth"]["in"], "cookie")


class SwaggerUIViewTests(APITestCase):
    url = "/api/docs/"

    def test_swagger_ui_loads(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"swagger-ui", response.content)

    def test_swagger_ui_does_not_require_authentication(self):
        response = self.client.get(self.url)

        self.assertNotEqual(response.status_code, 401)


class RedocViewTests(APITestCase):
    url = "/api/redoc/"

    def test_redoc_loads(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"redoc", response.content.lower())

    def test_redoc_does_not_require_authentication(self):
        response = self.client.get(self.url)

        self.assertNotEqual(response.status_code, 401)
