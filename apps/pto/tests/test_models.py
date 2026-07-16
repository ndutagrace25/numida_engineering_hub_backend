import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.pto.models import PTOEntry


class PTOEntryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.admin = User.objects.create_user(email="admin@example.com", password="pw")

    def test_valid_pto_entry_can_be_created(self):
        entry = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 17),
            reason="Family vacation.",
            handover_url="https://example.com/handover",
            created_by=self.admin,
        )

        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.created_by, self.admin)

    def test_reason_is_optional(self):
        entry = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 17),
            created_by=self.admin,
        )

        self.assertEqual(entry.reason, "")

    def test_handover_url_is_optional(self):
        entry = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 17),
            created_by=self.admin,
        )

        self.assertEqual(entry.handover_url, "")

    def test_end_date_before_start_date_is_rejected_through_model_validation(self):
        entry = PTOEntry(
            user=self.user,
            start_date=datetime.date(2026, 7, 17),
            end_date=datetime.date(2026, 7, 13),
            created_by=self.admin,
        )

        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_one_day_pto_entry_is_allowed(self):
        entry = PTOEntry(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 13),
            created_by=self.admin,
        )

        entry.full_clean()
        entry.save()

        self.assertEqual(entry.start_date, entry.end_date)

    def test_ordering_works_correctly(self):
        later = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 20),
            end_date=datetime.date(2026, 7, 21),
            created_by=self.admin,
        )
        earlier = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 14),
            created_by=self.admin,
        )

        self.assertEqual(list(PTOEntry.objects.all()), [earlier, later])

    def test_string_representation_is_readable(self):
        entry = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 17),
            created_by=self.admin,
        )

        self.assertEqual(str(entry), f"{self.user} — 2026-07-13 to 2026-07-17")

    def test_deleting_a_user_does_not_unexpectedly_remove_historical_pto_records(self):
        entry = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 17),
            created_by=self.admin,
        )

        self.user.delete()

        entry.refresh_from_db()
        self.assertIsNone(entry.user)
