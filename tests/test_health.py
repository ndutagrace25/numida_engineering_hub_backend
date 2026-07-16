from rest_framework.test import APITestCase

from common.constants import APPLICATION_NAME, APPLICATION_VERSION


class HealthCheckTests(APITestCase):
    url = "/health/"

    def test_returns_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_does_not_require_authentication(self):
        response = self.client.get(self.url)

        self.assertNotEqual(response.status_code, 401)

    def test_reports_expected_fields(self):
        response = self.client.get(self.url)

        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["application"], APPLICATION_NAME)
        self.assertEqual(data["version"], APPLICATION_VERSION)
        self.assertEqual(data["environment"], "test")
        self.assertIn("server_time", data)
