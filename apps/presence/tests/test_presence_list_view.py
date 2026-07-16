from django.utils import timezone

from apps.accounts.models import User
from apps.presence.models import UserPresence
from tests.base import BaseAPITestCase


class UserPresenceListViewTests(BaseAPITestCase):
    url = "/api/v1/presence/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.authenticate(self.user)

    def test_authenticated_user_can_retrieve_presence_list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "User presence retrieved successfully.")

    def test_response_groups_users_correctly(self):
        UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

        response = self.client.get(self.url)

        data = self.get_data(response)
        self.assertEqual(set(data.keys()), {"online", "recently_active", "offline"})
        self.assertEqual(data["online"][0]["user"]["display_name"], "Jane Doe")
        self.assertEqual(data["recently_active"], [])
        self.assertEqual(data["offline"], [])

    def test_active_user_without_presence_appears_as_offline(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        response = self.client.get(self.url)

        offline_ids = [u["user"]["id"] for u in self.get_data(response)["offline"]]
        self.assertIn(other.id, offline_ids)

    def test_sensitive_user_fields_are_not_exposed(self):
        UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

        response = self.client.get(self.url)

        user_data = self.get_data(response)["online"][0]["user"]
        self.assertNotIn("email", user_data)
        self.assertNotIn("password", user_data)
        self.assertNotIn("is_active", user_data)
        self.assertNotIn("is_staff", user_data)
        self.assertNotIn("is_superuser", user_data)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_query_count_does_not_grow_with_more_data(self):
        UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

        # A single select_related("presence") query over all active users,
        # regardless of how many have a presence row.
        with self.assertNumQueries(1):
            self.client.get(self.url)

        extra_users = [
            User.objects.create_user(email=f"extra{i}@example.com", password="pw") for i in range(5)
        ]
        for i, user in enumerate(extra_users):
            if i % 2 == 0:
                UserPresence.objects.create(user=user, last_seen_at=timezone.now())

        with self.assertNumQueries(1):
            self.client.get(self.url)
