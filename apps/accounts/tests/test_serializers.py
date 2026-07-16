from django.test import TestCase

from apps.accounts.models import User
from apps.accounts.serializers import CurrentUserSerializer, UserSerializer

EXPECTED_FIELDS = {
    "id",
    "email",
    "first_name",
    "last_name",
    "display_name",
    "is_active",
    "date_joined",
}


class UserSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com",
            password="s3cret-pw",
            first_name="Jane",
            last_name="Doe",
        )

    def test_returns_expected_fields(self):
        data = UserSerializer(self.user).data

        self.assertEqual(set(data.keys()), EXPECTED_FIELDS)

    def test_password_is_not_included(self):
        data = UserSerializer(self.user).data

        self.assertNotIn("password", data)

    def test_display_name_is_returned(self):
        data = UserSerializer(self.user).data

        self.assertEqual(data["display_name"], "Jane Doe")

    def test_read_only_fields_are_ignored_on_input(self):
        original_date_joined = self.user.date_joined

        serializer = UserSerializer(
            self.user,
            data={
                "id": 999,
                "email": "changed@example.com",
                "first_name": "Changed",
                "last_name": "Name",
                "display_name": "Someone Else",
                "is_active": False,
                "date_joined": "2000-01-01T00:00:00Z",
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertEqual(updated.id, self.user.id)
        self.assertEqual(updated.email, "jane@example.com")
        self.assertEqual(updated.first_name, "Jane")
        self.assertEqual(updated.last_name, "Doe")
        self.assertTrue(updated.is_active)
        self.assertEqual(updated.date_joined, original_date_joined)


class CurrentUserSerializerTests(TestCase):
    def test_returns_expected_fields(self):
        user = User.objects.create_user(email="jane@example.com", password="s3cret-pw")

        data = CurrentUserSerializer(user).data

        self.assertEqual(set(data.keys()), EXPECTED_FIELDS)

    def test_password_is_not_included(self):
        user = User.objects.create_user(email="jane@example.com", password="s3cret-pw")

        data = CurrentUserSerializer(user).data

        self.assertNotIn("password", data)
