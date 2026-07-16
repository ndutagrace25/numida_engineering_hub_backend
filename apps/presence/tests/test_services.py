import datetime

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.presence.models import UserPresence
from apps.presence.services import update_user_presence


class UpdateUserPresenceServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def test_presence_record_is_created_for_user_without_one(self):
        self.assertFalse(UserPresence.objects.filter(user=self.user).exists())

        update_user_presence(user=self.user)

        self.assertTrue(UserPresence.objects.filter(user=self.user).exists())

    def test_existing_presence_record_is_updated_not_duplicated(self):
        first = update_user_presence(user=self.user)

        second = update_user_presence(user=self.user)

        self.assertEqual(first.id, second.id)

    def test_last_seen_at_changes_to_current_time(self):
        old_time = timezone.now() - datetime.timedelta(hours=1)
        UserPresence.objects.create(user=self.user, last_seen_at=old_time)

        updated = update_user_presence(user=self.user)

        self.assertGreater(updated.last_seen_at, old_time)

    def test_only_one_presence_record_exists_per_user(self):
        update_user_presence(user=self.user)
        update_user_presence(user=self.user)
        update_user_presence(user=self.user)

        self.assertEqual(UserPresence.objects.filter(user=self.user).count(), 1)

    def test_correct_user_is_assigned(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        presence = update_user_presence(user=self.user)

        self.assertEqual(presence.user, self.user)
        self.assertFalse(UserPresence.objects.filter(user=other).exists())

    def test_service_returns_the_updated_presence_instance(self):
        presence = update_user_presence(user=self.user)

        self.assertIsInstance(presence, UserPresence)
        self.assertEqual(presence.user, self.user)
