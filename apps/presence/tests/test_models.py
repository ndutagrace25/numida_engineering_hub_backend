from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.presence.models import UserPresence


class UserPresenceModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def test_presence_record_can_be_created(self):
        now = timezone.now()

        presence = UserPresence.objects.create(user=self.user, last_seen_at=now)

        self.assertEqual(presence.user, self.user)

    def test_user_cannot_have_more_than_one_presence_record(self):
        UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

        with self.assertRaises(IntegrityError):
            UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

    def test_last_seen_at_is_stored_correctly(self):
        now = timezone.now()

        presence = UserPresence.objects.create(user=self.user, last_seen_at=now)

        presence.refresh_from_db()
        self.assertEqual(presence.last_seen_at, now)

    def test_string_representation_is_readable(self):
        now = timezone.now()

        presence = UserPresence.objects.create(user=self.user, last_seen_at=now)

        self.assertEqual(str(presence), f"{self.user} — last seen {now}")

    def test_deleting_user_deletes_presence_record(self):
        presence = UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())
        presence_id = presence.id

        self.user.delete()

        self.assertFalse(UserPresence.objects.filter(id=presence_id).exists())
