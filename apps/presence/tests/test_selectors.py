import datetime

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.presence.models import UserPresence
from apps.presence.selectors import list_user_presence


class ListUserPresenceSelectorTests(TestCase):
    def _presence(self, user, minutes_ago):
        return UserPresence.objects.create(
            user=user, last_seen_at=timezone.now() - datetime.timedelta(minutes=minutes_ago)
        )

    def test_online_users_are_grouped_correctly(self):
        user = User.objects.create_user(email="jane@example.com", password="pw")
        self._presence(user, 0)

        data = list_user_presence()

        self.assertEqual([entry["user"].id for entry in data["online"]], [user.id])
        self.assertEqual(data["recently_active"], [])
        self.assertEqual(data["offline"], [])

    def test_recently_active_users_are_grouped_correctly(self):
        user = User.objects.create_user(email="jane@example.com", password="pw")
        self._presence(user, 10)

        data = list_user_presence()

        self.assertEqual([entry["user"].id for entry in data["recently_active"]], [user.id])
        self.assertEqual(data["online"], [])
        self.assertEqual(data["offline"], [])

    def test_offline_users_are_grouped_correctly(self):
        user = User.objects.create_user(email="jane@example.com", password="pw")
        self._presence(user, 20)

        data = list_user_presence()

        self.assertEqual([entry["user"].id for entry in data["offline"]], [user.id])
        self.assertEqual(data["online"], [])
        self.assertEqual(data["recently_active"], [])

    def test_active_users_without_presence_record_are_included_as_offline(self):
        user = User.objects.create_user(email="jane@example.com", password="pw")

        data = list_user_presence()

        entry = next(e for e in data["offline"] if e["user"].id == user.id)
        self.assertIsNone(entry["last_seen_at"])

    def test_inactive_users_are_excluded(self):
        user = User.objects.create_user(email="jane@example.com", password="pw", is_active=False)
        self._presence(user, 0)

        data = list_user_presence()

        all_ids = {entry["user"].id for group in data.values() for entry in group}
        self.assertNotIn(user.id, all_ids)

    def test_users_are_ordered_alphabetically_within_each_group(self):
        zed = User.objects.create_user(
            email="zed@example.com", password="pw", first_name="Zed", last_name="Smith"
        )
        amina = User.objects.create_user(
            email="amina@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )
        self._presence(zed, 0)
        self._presence(amina, 0)

        data = list_user_presence()

        self.assertEqual([entry["user"].id for entry in data["online"]], [amina.id, zed.id])

    def test_avoids_unnecessary_database_queries(self):
        for i in range(5):
            user = User.objects.create_user(email=f"user{i}@example.com", password="pw")
            if i % 2 == 0:
                self._presence(user, 0)

        with self.assertNumQueries(1):
            data = list_user_presence()
            for group in data.values():
                for entry in group:
                    _ = entry["user"].first_name
