import datetime

from apps.accounts.models import User
from apps.aob.services import create_aob_item
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


class AOBItemDetailViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.item = create_aob_item(
            created_by=self.user,
            validated_data={
                "title": "Office move",
                "description": "",
                "external_url": "",
                "week_start": MONDAY,
                "position": 1,
            },
        )

    def _url(self, item_id=None):
        return f"/api/v1/aob-items/{item_id or self.item.id}/"

    def test_authenticated_user_can_retrieve_their_own_item(self):
        self.authenticate(self.user)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "AOB item retrieved successfully.")

    def test_authenticated_user_can_retrieve_another_users_item(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        data = self.get_data(response)
        self.assertEqual(data["id"], self.item.id)

    def test_nonexistent_item_returns_standard_404(self):
        self.authenticate(self.user)

        response = self.client.get(self._url(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")

    def test_unauthenticated_requests_are_rejected(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_sensitive_creator_fields_are_not_exposed(self):
        self.authenticate(self.user)

        response = self.client.get(self._url())

        creator = self.get_data(response)["created_by"]
        self.assertNotIn("email", creator)
        self.assertNotIn("password", creator)
        self.assertNotIn("is_active", creator)
        self.assertNotIn("is_staff", creator)
        self.assertNotIn("is_superuser", creator)
