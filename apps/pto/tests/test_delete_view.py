import datetime

from apps.accounts.models import User
from apps.pto.models import PTOEntry
from apps.pto.services import create_pto_entry
from tests.base import BaseAPITestCase


class PTOEntryDeleteViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")
        self.entry = create_pto_entry(
            created_by=self.creator,
            validated_data={
                "user": self.user,
                "start_date": datetime.date(2026, 7, 13),
                "end_date": datetime.date(2026, 7, 17),
            },
        )
        self.authenticate(self.creator)

    def _url(self, entry_id=None):
        return f"/api/v1/pto/{entry_id or self.entry.id}/"

    def test_creator_can_delete_the_entry(self):
        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"message": "PTO entry deleted successfully.", "data": None}
        )
        self.assertFalse(PTOEntry.objects.filter(id=self.entry.id).exists())

    def test_another_user_cannot_delete_the_entry(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_error(response)["code"], "PERMISSION_DENIED")
        self.assertTrue(PTOEntry.objects.filter(id=self.entry.id).exists())

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 401)
        self.assertTrue(PTOEntry.objects.filter(id=self.entry.id).exists())

    def test_nonexistent_entry_returns_standard_404(self):
        response = self.client.delete(self._url(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")
