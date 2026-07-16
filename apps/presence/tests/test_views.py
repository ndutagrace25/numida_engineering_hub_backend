import datetime

from django.utils import timezone

from apps.accounts.models import User
from apps.presence.models import UserPresence
from tests.base import BaseAPITestCase


class HeartbeatViewTests(BaseAPITestCase):
    url = "/api/v1/presence/heartbeat/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.authenticate(self.user)

    def test_authenticated_users_can_update_their_presence(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Presence updated successfully.")

    def test_presence_record_is_created_if_one_does_not_exist(self):
        self.assertFalse(UserPresence.objects.filter(user=self.user).exists())

        self.client.post(self.url)

        self.assertTrue(UserPresence.objects.filter(user=self.user).exists())

    def test_existing_presence_records_are_updated_not_duplicated(self):
        self.client.post(self.url)

        self.client.post(self.url)

        self.assertEqual(UserPresence.objects.filter(user=self.user).count(), 1)

    def test_last_seen_at_changes_after_multiple_heartbeat_requests(self):
        old_time = timezone.now() - datetime.timedelta(hours=1)
        UserPresence.objects.create(user=self.user, last_seen_at=old_time)

        response = self.client.post(self.url)

        data = self.get_data(response)
        self.assertGreater(
            datetime.datetime.fromisoformat(data["last_seen_at"]),
            old_time,
        )

    def test_response_returns_the_correct_status(self):
        response = self.client.post(self.url)

        data = self.get_data(response)
        self.assertEqual(data["status"], "ONLINE")

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_sensitive_user_information_is_not_exposed(self):
        response = self.client.post(self.url)

        user_data = self.get_data(response)["user"]
        self.assertNotIn("email", user_data)
        self.assertNotIn("password", user_data)
        self.assertNotIn("is_active", user_data)
        self.assertNotIn("is_staff", user_data)
        self.assertNotIn("is_superuser", user_data)
