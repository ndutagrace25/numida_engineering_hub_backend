import datetime

from apps.accounts.models import User
from apps.aob.models import AOBItem
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


def _valid_payload(**overrides):
    data = {
        "title": "Office move",
        "description": "We're moving floors next month.",
        "external_url": "https://example.com/office-move",
        "week_start": MONDAY.isoformat(),
        "position": 1,
    }
    data.update(overrides)
    return data


class AOBItemCreateViewTests(BaseAPITestCase):
    url = "/api/v1/aob-items/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.authenticate(self.user)

    def test_authenticated_user_can_create_a_valid_aob_item(self):
        response = self.client.post(self.url, _valid_payload(), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "AOB item created successfully.")

    def test_authenticated_user_is_assigned_as_created_by(self):
        response = self.client.post(self.url, _valid_payload(), format="json")

        data = self.get_data(response)
        self.assertEqual(data["created_by"]["id"], self.user.id)

        item = AOBItem.objects.get(pk=data["id"])
        self.assertEqual(item.created_by, self.user)

    def test_description_may_be_blank(self):
        response = self.client.post(self.url, _valid_payload(description=""), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.get_data(response)["description"], "")

    def test_external_url_may_be_omitted(self):
        payload = _valid_payload()
        del payload["external_url"]

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.get_data(response)["external_url"], "")

    def test_invalid_http_urls_are_rejected(self):
        response = self.client.post(
            self.url,
            _valid_payload(external_url="http://example.com/office-move"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("external_url", error["fields"])

    def test_non_monday_week_start_is_rejected(self):
        response = self.client.post(
            self.url, _valid_payload(week_start="2026-07-14"), format="json"
        )  # Tuesday

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("week_start", error["fields"])

    def test_negative_position_is_rejected(self):
        response = self.client.post(self.url, _valid_payload(position=-1), format="json")

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("position", error["fields"])

    def test_request_data_cannot_override_created_by(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        response = self.client.post(self.url, _valid_payload(created_by=other.id), format="json")

        data = self.get_data(response)
        self.assertEqual(data["created_by"]["id"], self.user.id)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, _valid_payload(), format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_validation_errors_use_standard_error_format(self):
        response = self.client.post(self.url, _valid_payload(title="   "), format="json")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(set(body["error"].keys()), {"code", "message", "fields"})

    def test_sensitive_creator_fields_are_not_exposed(self):
        response = self.client.post(self.url, _valid_payload(), format="json")

        creator = self.get_data(response)["created_by"]
        self.assertNotIn("email", creator)
        self.assertNotIn("password", creator)
        self.assertNotIn("is_active", creator)
        self.assertNotIn("is_staff", creator)
        self.assertNotIn("is_superuser", creator)
