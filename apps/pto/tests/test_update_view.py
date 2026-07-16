import datetime

from apps.accounts.models import User
from apps.pto.services import create_pto_entry
from tests.base import BaseAPITestCase


class PTOEntryUpdateViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")
        self.entry = create_pto_entry(
            created_by=self.creator,
            validated_data={
                "user": self.user,
                "start_date": datetime.date(2026, 7, 13),
                "end_date": datetime.date(2026, 7, 17),
                "reason": "Original reason.",
            },
        )
        self.authenticate(self.creator)

    def _url(self, entry_id=None):
        return f"/api/v1/pto/{entry_id or self.entry.id}/"

    def test_creator_can_update_the_entry(self):
        response = self.client.patch(self._url(), {"reason": "New reason."}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_data(response)["reason"], "New reason.")

    def test_created_by_cannot_be_changed(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        response = self.client.patch(
            self._url(), {"reason": "New reason.", "created_by": other.id}, format="json"
        )

        data = self.get_data(response)
        self.assertEqual(data["created_by"]["id"], self.creator.id)

    def test_another_user_cannot_update_the_entry(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.patch(self._url(), {"reason": "Hijacked."}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_error(response)["code"], "PERMISSION_DENIED")

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.patch(self._url(), {"reason": "x"}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_nonexistent_entry_returns_standard_404(self):
        response = self.client.patch(self._url(999999), {"reason": "x"}, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")
