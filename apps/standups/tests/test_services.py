import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.standups.models import Standup, StandupItem
from apps.standups.services import create_standup


def _valid_items():
    return [
        {"section": "COMPLETED", "content": "Shipped the login endpoint.", "position": 1},
        {"section": "CURRENT", "content": "Working on the standups API.", "position": 1},
        {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 2},
    ]


class CreateStandupServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def _validated_data(self, **overrides):
        data = {
            "standup_date": datetime.date(2026, 7, 13),
            "blockers": "",
            "items": _valid_items(),
        }
        data.update(overrides)
        return data

    def test_standup_and_all_nested_items_are_created(self):
        standup = create_standup(user=self.user, validated_data=self._validated_data())

        self.assertEqual(Standup.objects.count(), 1)
        self.assertEqual(standup.items.count(), 3)

    def test_authenticated_user_is_assigned_as_owner(self):
        standup = create_standup(user=self.user, validated_data=self._validated_data())

        self.assertEqual(standup.user, self.user)

    def test_duplicate_standup_for_same_user_and_date_is_rejected(self):
        create_standup(user=self.user, validated_data=self._validated_data())

        with self.assertRaises(IntegrityError):
            create_standup(user=self.user, validated_data=self._validated_data())

    def test_different_users_can_create_standups_for_the_same_date(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        create_standup(user=self.user, validated_data=self._validated_data())
        create_standup(user=other, validated_data=self._validated_data())

        count = Standup.objects.filter(standup_date=datetime.date(2026, 7, 13)).count()
        self.assertEqual(count, 2)

    def test_rollback_when_item_creation_fails(self):
        items = _valid_items()
        items[1]["content"] = None  # violates the NOT NULL constraint on content

        with self.assertRaises(IntegrityError):
            create_standup(user=self.user, validated_data=self._validated_data(items=items))

        self.assertEqual(Standup.objects.count(), 0)
        self.assertEqual(StandupItem.objects.count(), 0)

    def test_meetings_are_optional(self):
        # _valid_items() has no MEETING-section item at all.
        standup = create_standup(user=self.user, validated_data=self._validated_data())

        self.assertFalse(standup.items.filter(section=StandupItem.Section.MEETING).exists())

    def test_blockers_are_saved_correctly(self):
        standup = create_standup(
            user=self.user,
            validated_data=self._validated_data(blockers="Waiting on API access."),
        )

        self.assertEqual(standup.blockers, "Waiting on API access.")

    def test_item_positions_are_preserved(self):
        items = _valid_items()
        items[2]["position"] = 5

        standup = create_standup(user=self.user, validated_data=self._validated_data(items=items))

        planned_item = standup.items.get(section=StandupItem.Section.PLANNED)
        self.assertEqual(planned_item.position, 5)
