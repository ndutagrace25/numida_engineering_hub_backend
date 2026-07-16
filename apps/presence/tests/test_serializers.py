import datetime

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.presence.models import PresenceStatus, UserPresence
from apps.presence.serializers import UserPresenceSerializer


class UserPresenceSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )

    def test_returns_expected_user_fields(self):
        presence = UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

        data = UserPresenceSerializer(presence).data

        self.assertEqual(
            set(data["user"].keys()), {"id", "first_name", "last_name", "display_name"}
        )
        self.assertEqual(data["user"]["display_name"], "Jane Doe")

    def test_sensitive_user_fields_are_not_exposed(self):
        presence = UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

        data = UserPresenceSerializer(presence).data

        self.assertNotIn("email", data["user"])
        self.assertNotIn("password", data["user"])
        self.assertNotIn("is_active", data["user"])
        self.assertNotIn("is_staff", data["user"])
        self.assertNotIn("is_superuser", data["user"])

    def test_status_is_read_only(self):
        presence = UserPresence.objects.create(
            user=self.user, last_seen_at=timezone.now() - datetime.timedelta(minutes=20)
        )

        serializer = UserPresenceSerializer(
            presence,
            data={"status": "ONLINE", "last_seen_at": timezone.now()},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("status", serializer.validated_data)

    def test_status_reflects_online(self):
        presence = UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

        data = UserPresenceSerializer(presence).data

        self.assertEqual(data["status"], PresenceStatus.ONLINE)

    def test_status_reflects_recently_active(self):
        presence = UserPresence.objects.create(
            user=self.user, last_seen_at=timezone.now() - datetime.timedelta(minutes=10)
        )

        data = UserPresenceSerializer(presence).data

        self.assertEqual(data["status"], PresenceStatus.RECENTLY_ACTIVE)

    def test_status_reflects_offline(self):
        presence = UserPresence.objects.create(
            user=self.user, last_seen_at=timezone.now() - datetime.timedelta(minutes=20)
        )

        data = UserPresenceSerializer(presence).data

        self.assertEqual(data["status"], PresenceStatus.OFFLINE)
