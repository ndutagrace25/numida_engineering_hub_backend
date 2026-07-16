import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.aob.models import AOBItem

MONDAY = datetime.date(2026, 7, 13)


class AOBItemModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def test_valid_aob_item_can_be_created(self):
        item = AOBItem.objects.create(
            title="Office move",
            description="We're moving floors next month.",
            external_url="https://example.com/office-move",
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        self.assertEqual(item.title, "Office move")
        self.assertEqual(item.created_by, self.user)

    def test_description_and_external_url_are_optional(self):
        item = AOBItem.objects.create(
            title="Office move", week_start=MONDAY, position=1, created_by=self.user
        )

        self.assertEqual(item.description, "")
        self.assertEqual(item.external_url, "")

    def test_non_monday_week_start_is_rejected_through_model_validation(self):
        item = AOBItem(
            title="Office move",
            week_start=datetime.date(2026, 7, 14),  # a Tuesday
            position=1,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_items_are_ordered_correctly(self):
        older_week = AOBItem.objects.create(
            title="A", week_start=datetime.date(2026, 7, 6), position=1, created_by=self.user
        )
        newer_week_second = AOBItem.objects.create(
            title="B", week_start=MONDAY, position=2, created_by=self.user
        )
        newer_week_first = AOBItem.objects.create(
            title="C", week_start=MONDAY, position=1, created_by=self.user
        )

        self.assertEqual(
            list(AOBItem.objects.all()),
            [newer_week_first, newer_week_second, older_week],
        )

    def test_deleting_a_user_does_not_delete_historical_aob_items(self):
        item = AOBItem.objects.create(
            title="Office move", week_start=MONDAY, position=1, created_by=self.user
        )

        self.user.delete()

        item.refresh_from_db()
        self.assertIsNone(item.created_by)

    def test_string_representation_is_readable(self):
        item = AOBItem.objects.create(
            title="Office move", week_start=MONDAY, position=1, created_by=self.user
        )

        self.assertEqual(str(item), f"Office move — week of {MONDAY}")
