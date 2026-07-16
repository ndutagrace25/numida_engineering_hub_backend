import datetime

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.standups.models import Standup, StandupItem


class StandupModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def test_standup_can_be_created(self):
        standup = Standup.objects.create(
            user=self.user,
            standup_date=datetime.date(2026, 7, 13),
            blockers="Waiting on API access.",
        )

        self.assertEqual(standup.user, self.user)
        self.assertEqual(standup.standup_date, datetime.date(2026, 7, 13))
        self.assertEqual(standup.blockers, "Waiting on API access.")

    def test_blockers_is_optional(self):
        standup = Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))

        self.assertEqual(standup.blockers, "")

    def test_duplicate_standup_for_same_user_and_date_is_rejected(self):
        Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))

        with self.assertRaises(IntegrityError):
            Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))

    def test_user_can_have_standups_on_different_dates(self):
        Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))
        Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 14))

        self.assertEqual(Standup.objects.filter(user=self.user).count(), 2)

    def test_different_users_can_submit_on_the_same_date(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))
        Standup.objects.create(user=other, standup_date=datetime.date(2026, 7, 13))

        self.assertEqual(Standup.objects.filter(standup_date=datetime.date(2026, 7, 13)).count(), 2)

    def test_deleting_standup_deletes_its_items(self):
        standup = Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))
        StandupItem.objects.create(
            standup=standup,
            section=StandupItem.Section.COMPLETED,
            content="Shipped the login endpoint.",
            position=1,
        )

        standup.delete()

        self.assertEqual(StandupItem.objects.count(), 0)

    def test_default_ordering_is_newest_standup_date_first(self):
        older = Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 10))
        newer = Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 15))

        self.assertEqual(list(Standup.objects.all()), [newer, older])

    def test_string_representation_is_readable(self):
        standup = Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))

        self.assertEqual(str(standup), f"{self.user} — 2026-07-13")


class StandupItemModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.standup = Standup.objects.create(
            user=self.user, standup_date=datetime.date(2026, 7, 13)
        )

    def test_standup_item_can_be_created_for_each_valid_section(self):
        for position, section in enumerate(StandupItem.Section.values, start=1):
            item = StandupItem.objects.create(
                standup=self.standup,
                section=section,
                content=f"Content for {section}",
                position=position,
            )
            self.assertEqual(item.section, section)

        self.assertEqual(self.standup.items.count(), len(StandupItem.Section.values))

    def test_items_related_name_on_standup(self):
        item = StandupItem.objects.create(
            standup=self.standup,
            section=StandupItem.Section.CURRENT,
            content="Working on the standups API.",
            position=1,
        )

        self.assertIn(item, self.standup.items.all())

    def test_default_ordering_is_by_section_then_position(self):
        meeting = StandupItem.objects.create(
            standup=self.standup, section=StandupItem.Section.MEETING, content="Standup", position=1
        )
        completed_2 = StandupItem.objects.create(
            standup=self.standup,
            section=StandupItem.Section.COMPLETED,
            content="Second",
            position=2,
        )
        completed_1 = StandupItem.objects.create(
            standup=self.standup, section=StandupItem.Section.COMPLETED, content="First", position=1
        )

        self.assertEqual(
            list(self.standup.items.all()),
            [completed_1, completed_2, meeting],
        )

    def test_invalid_section_is_rejected_through_model_validation(self):
        item = StandupItem(
            standup=self.standup,
            section="NOT_A_REAL_SECTION",
            content="Something",
            position=1,
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_string_representation_is_readable(self):
        item = StandupItem.objects.create(
            standup=self.standup,
            section=StandupItem.Section.COMPLETED,
            content="Shipped the login endpoint.",
            position=1,
        )

        self.assertEqual(str(item), f"{self.standup} — What did I do? #1")
