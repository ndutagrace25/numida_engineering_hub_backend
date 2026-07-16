from apps.accounts.models import User
from apps.standups.models import Standup
from tests.base import BaseAPITestCase


def _valid_items():
    return [
        {"section": "COMPLETED", "content": "Shipped the login endpoint.", "position": 1},
        {"section": "CURRENT", "content": "Working on the standups API.", "position": 1},
        {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 1},
    ]


class StandupCreateViewTests(BaseAPITestCase):
    url = "/api/v1/standups/"

    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.authenticate(self.user)

    def _payload(self, **overrides):
        data = {
            "standup_date": "2026-07-16",
            "blockers": "",
            "items": _valid_items(),
        }
        data.update(overrides)
        return data

    def test_authenticated_user_can_create_a_valid_standup(self):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "Standup submitted successfully.")

    def test_authenticated_user_becomes_the_owner(self):
        response = self.client.post(self.url, self._payload(), format="json")

        data = self.get_data(response)
        self.assertEqual(data["user"]["email"], "jane@example.com")
        standup = Standup.objects.get(pk=data["id"])
        self.assertEqual(standup.user, self.user)

    def test_nested_standup_items_are_created(self):
        response = self.client.post(self.url, self._payload(), format="json")

        data = self.get_data(response)
        self.assertEqual(len(data["items"]), 3)
        standup = Standup.objects.get(pk=data["id"])
        self.assertEqual(standup.items.count(), 3)

    def test_meetings_are_optional(self):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201)

    def test_blockers_are_optional(self):
        payload = self._payload()
        del payload["blockers"]

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201)

    def test_missing_required_sections_are_rejected(self):
        items = [item for item in _valid_items() if item["section"] != "COMPLETED"]

        response = self.client.post(self.url, self._payload(items=items), format="json")

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("items", error["fields"])

    def test_duplicate_standup_date_for_same_user_is_rejected(self):
        self.client.post(self.url, self._payload(), format="json")

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("standup_date", error["fields"])

    def test_different_users_can_submit_for_the_same_date(self):
        self.client.post(self.url, self._payload(), format="json")

        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_invalid_requests_use_standard_error_format(self):
        response = self.client.post(self.url, self._payload(items=[]), format="json")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(set(body["error"].keys()), {"code", "message", "fields"})

    def test_response_does_not_expose_sensitive_user_fields(self):
        response = self.client.post(self.url, self._payload(), format="json")

        user_data = self.get_data(response)["user"]
        self.assertNotIn("password", user_data)
        self.assertNotIn("is_staff", user_data)
        self.assertNotIn("is_superuser", user_data)
