import datetime

from apps.accounts.models import User
from apps.pto.services import create_pto_entry
from tests.base import BaseAPITestCase


class PTOEntryDetailViewTests(BaseAPITestCase):
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

    def _url(self, entry_id=None):
        return f"/api/v1/pto/{entry_id or self.entry.id}/"

    def test_any_authenticated_user_can_view_detail(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "PTO entry retrieved successfully.")

    def test_nonexistent_entry_returns_standard_404(self):
        self.authenticate(self.creator)

        response = self.client.get(self._url(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")

    def test_unauthenticated_requests_are_rejected(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
