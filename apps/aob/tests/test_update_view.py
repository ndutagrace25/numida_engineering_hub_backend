import datetime

from apps.accounts.models import User
from apps.aob.services import create_aob_item
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


class AOBItemUpdateViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.item = create_aob_item(
            created_by=self.user,
            validated_data={
                "title": "Office move",
                "description": "Original description.",
                "external_url": "https://example.com/original",
                "week_start": MONDAY,
                "position": 1,
            },
        )
        self.authenticate(self.user)

    def _url(self, item_id=None):
        return f"/api/v1/aob-items/{item_id or self.item.id}/"

    def test_creator_can_update_the_item(self):
        response = self.client.patch(self._url(), {"title": "New title"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "AOB item updated successfully.")

    def test_all_editable_fields_update_correctly(self):
        payload = {
            "title": "New title",
            "description": "New description.",
            "external_url": "https://example.com/new",
            "week_start": "2026-07-20",
            "position": 5,
        }

        response = self.client.patch(self._url(), payload, format="json")

        data = self.get_data(response)
        self.assertEqual(data["title"], "New title")
        self.assertEqual(data["description"], "New description.")
        self.assertEqual(data["external_url"], "https://example.com/new")
        self.assertEqual(data["week_start"], "2026-07-20")
        self.assertEqual(data["position"], 5)

    def test_description_can_be_cleared(self):
        response = self.client.patch(self._url(), {"description": ""}, format="json")

        self.assertEqual(self.get_data(response)["description"], "")

    def test_external_url_can_be_cleared(self):
        response = self.client.patch(self._url(), {"external_url": ""}, format="json")

        self.assertEqual(self.get_data(response)["external_url"], "")

    def test_created_by_remains_unchanged(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        response = self.client.patch(
            self._url(), {"title": "New title", "created_by": other.id}, format="json"
        )

        data = self.get_data(response)
        self.assertEqual(data["created_by"]["id"], self.user.id)

    def test_another_authenticated_user_cannot_update_the_item(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.patch(self._url(), {"title": "Hijacked"}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_error(response)["code"], "PERMISSION_DENIED")

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.patch(self._url(), {"title": "New title"}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_nonexistent_item_returns_standard_404(self):
        response = self.client.patch(self._url(999999), {"title": "New title"}, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")

    def test_invalid_data_uses_standard_error_format(self):
        response = self.client.patch(self._url(), {"title": "   "}, format="json")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(set(body["error"].keys()), {"code", "message", "fields"})
