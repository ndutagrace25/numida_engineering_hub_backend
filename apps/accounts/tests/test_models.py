from django.db.utils import IntegrityError
from django.test import TestCase

from apps.accounts.models import User


class UserManagerTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(email="jane@example.com", password="s3cret-pw")

        self.assertEqual(user.email, "jane@example.com")
        self.assertTrue(user.check_password("s3cret-pw"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="admin@example.com", password="s3cret-pw")

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser_rejects_is_staff_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="s3cret-pw", is_staff=False
            )

    def test_create_superuser_rejects_is_superuser_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="s3cret-pw", is_superuser=False
            )

    def test_email_is_normalized(self):
        user = User.objects.create_user(email="jane@EXAMPLE.COM", password="s3cret-pw")

        self.assertEqual(user.email, "jane@example.com")

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="s3cret-pw")


class UserModelTests(TestCase):
    def test_email_must_be_unique(self):
        User.objects.create_user(email="jane@example.com", password="s3cret-pw")

        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="jane@example.com", password="other-pw")

    def test_display_name_uses_full_name_when_present(self):
        user = User.objects.create_user(
            email="jane@example.com",
            password="s3cret-pw",
            first_name="Jane",
            last_name="Doe",
        )

        self.assertEqual(user.display_name, "Jane Doe")

    def test_display_name_falls_back_to_email(self):
        user = User.objects.create_user(email="jane@example.com", password="s3cret-pw")

        self.assertEqual(user.display_name, "jane@example.com")

    def test_string_representation_is_email(self):
        user = User.objects.create_user(email="jane@example.com", password="s3cret-pw")

        self.assertEqual(str(user), "jane@example.com")
