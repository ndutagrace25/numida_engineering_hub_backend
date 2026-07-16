import datetime

from apps.accounts.models import User
from apps.standups.services import create_standup
from tests.base import BaseAPITestCase


def _shuffled_items():
    return [
        {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 1},
        {"section": "COMPLETED", "content": "Shipped the login endpoint.", "position": 1},
        {"section": "CURRENT", "content": "Working on the standups API.", "position": 1},
    ]


class StandupDetailViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.standup = create_standup(
            user=self.user,
            validated_data={
                "standup_date": datetime.date(2026, 7, 13),
                "blockers": "",
                "items": _shuffled_items(),
            },
        )

    def _url(self, standup_id=None):
        return f"/api/v1/standups/{standup_id or self.standup.id}/"

    def test_authenticated_user_can_retrieve_their_own_standup(self):
        self.authenticate(self.user)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Standup retrieved successfully.")

    def test_authenticated_user_can_retrieve_another_users_standup(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        data = self.get_data(response)
        self.assertEqual(data["id"], self.standup.id)

    def test_nested_items_are_returned(self):
        self.authenticate(self.user)

        response = self.client.get(self._url())

        data = self.get_data(response)
        self.assertEqual(len(data["items"]), 3)

    def test_items_are_ordered_correctly(self):
        self.authenticate(self.user)

        response = self.client.get(self._url())

        sections = [item["section"] for item in self.get_data(response)["items"]]
        self.assertEqual(sections, ["COMPLETED", "CURRENT", "PLANNED"])

    def test_nonexistent_standup_returns_standard_404(self):
        self.authenticate(self.user)

        response = self.client.get(self._url(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")

    def test_unauthenticated_requests_are_rejected(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_sensitive_user_fields_are_not_exposed(self):
        self.authenticate(self.user)

        response = self.client.get(self._url())

        user_data = self.get_data(response)["user"]
        self.assertNotIn("password", user_data)
        self.assertNotIn("is_staff", user_data)
        self.assertNotIn("is_superuser", user_data)
