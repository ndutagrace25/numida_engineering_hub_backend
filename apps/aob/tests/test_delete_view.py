import datetime

from apps.accounts.models import User
from apps.aob.models import AOBItem
from apps.aob.services import create_aob_item
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


class AOBItemDeleteViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.item = create_aob_item(
            user=self.user,
            validated_data={
                "title": "Office move",
                "description": "",
                "external_url": "",
                "week_start": MONDAY,
                "position": 1,
            },
        )
        self.authenticate(self.user)

    def _url(self, item_id=None):
        return f"/api/v1/aob-items/{item_id or self.item.id}/"

    def test_creator_can_delete_the_item(self):
        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 200)

    def test_response_follows_the_standard_success_format(self):
        response = self.client.delete(self._url())

        self.assertEqual(
            response.json(), {"message": "AOB item deleted successfully.", "data": None}
        )

    def test_item_is_removed_from_the_database(self):
        self.client.delete(self._url())

        self.assertFalse(AOBItem.objects.filter(id=self.item.id).exists())

    def test_deleting_one_item_does_not_affect_other_aob_items(self):
        other_item = create_aob_item(
            user=self.user,
            validated_data={
                "title": "Other item",
                "description": "",
                "external_url": "",
                "week_start": MONDAY + datetime.timedelta(days=7),
                "position": 1,
            },
        )

        self.client.delete(self._url())

        self.assertTrue(AOBItem.objects.filter(id=other_item.id).exists())

    def test_another_authenticated_user_cannot_delete_the_item(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_error(response)["code"], "PERMISSION_DENIED")
        self.assertTrue(AOBItem.objects.filter(id=self.item.id).exists())

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
        self.assertTrue(AOBItem.objects.filter(id=self.item.id).exists())

    def test_nonexistent_item_returns_standard_404(self):
        response = self.client.delete(self._url(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")
