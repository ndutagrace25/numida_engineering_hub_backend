import datetime

from apps.accounts.models import User
from apps.standups.models import Standup, StandupItem
from apps.standups.services import create_standup
from tests.base import BaseAPITestCase


def _valid_items():
    return [
        {"section": "COMPLETED", "content": "Shipped the login endpoint.", "position": 1},
        {"section": "CURRENT", "content": "Working on the standups API.", "position": 1},
        {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 1},
    ]


class StandupDeleteViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.standup = create_standup(
            user=self.user,
            validated_data={
                "standup_date": datetime.date(2026, 7, 13),
                "blockers": "",
                "items": _valid_items(),
            },
        )
        self.authenticate(self.user)

    def _url(self, standup_id=None):
        return f"/api/v1/standups/{standup_id or self.standup.id}/"

    def test_owner_can_delete_their_standup(self):
        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Standup.objects.filter(id=self.standup.id).exists())

    def test_response_follows_standard_success_format(self):
        response = self.client.delete(self._url())

        self.assertEqual(
            response.json(), {"message": "Standup deleted successfully.", "data": None}
        )

    def test_related_standup_items_are_removed_after_deletion(self):
        item_ids = list(self.standup.items.values_list("id", flat=True))

        self.client.delete(self._url())

        self.assertFalse(StandupItem.objects.filter(id__in=item_ids).exists())

    def test_another_authenticated_user_cannot_delete_someone_elses_standup(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_error(response)["code"], "PERMISSION_DENIED")
        self.assertTrue(Standup.objects.filter(id=self.standup.id).exists())

    def test_unauthenticated_users_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
        self.assertTrue(Standup.objects.filter(id=self.standup.id).exists())

    def test_deleting_a_nonexistent_standup_returns_404(self):
        response = self.client.delete(self._url(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")
