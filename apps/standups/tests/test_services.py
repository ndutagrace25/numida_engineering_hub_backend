import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.standups.models import Standup, StandupItem
from apps.standups.services import create_standup, update_standup


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


class UpdateStandupServiceTests(TestCase):
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

    def _create(self, **overrides):
        return create_standup(user=self.user, validated_data=self._validated_data(**overrides))

    def test_standup_fields_are_updated_successfully(self):
        standup = self._create()

        updated = update_standup(
            standup=standup,
            validated_data=self._validated_data(
                standup_date=datetime.date(2026, 7, 20), blockers="Blocked on review."
            ),
        )

        updated.refresh_from_db()
        self.assertEqual(updated.standup_date, datetime.date(2026, 7, 20))
        self.assertEqual(updated.blockers, "Blocked on review.")

    def test_existing_items_are_replaced_with_new_items(self):
        standup = self._create()

        new_items = [
            {"section": "COMPLETED", "content": "Different work.", "position": 1},
            {"section": "CURRENT", "content": "Different task.", "position": 1},
            {"section": "PLANNED", "content": "Different plan.", "position": 1},
        ]
        update_standup(standup=standup, validated_data=self._validated_data(items=new_items))

        contents = set(standup.items.values_list("content", flat=True))
        self.assertEqual(contents, {"Different work.", "Different task.", "Different plan."})

    def test_removed_items_no_longer_exist(self):
        standup = self._create()
        old_item_ids = list(standup.items.values_list("id", flat=True))

        update_standup(standup=standup, validated_data=self._validated_data())

        self.assertFalse(StandupItem.objects.filter(id__in=old_item_ids).exists())

    def test_new_items_are_created_correctly(self):
        standup = self._create()

        new_items = [
            {"section": "COMPLETED", "content": "New completed.", "position": 1},
            {"section": "CURRENT", "content": "New current.", "position": 1},
            {"section": "PLANNED", "content": "New planned.", "position": 1},
            {"section": "MEETING", "content": "Standup sync.", "position": 1},
        ]
        update_standup(standup=standup, validated_data=self._validated_data(items=new_items))

        self.assertEqual(standup.items.count(), 4)
        meeting = standup.items.get(section=StandupItem.Section.MEETING)
        self.assertEqual(meeting.content, "Standup sync.")

    def test_item_positions_are_preserved(self):
        standup = self._create()

        new_items = _valid_items()
        new_items[2]["position"] = 7
        update_standup(standup=standup, validated_data=self._validated_data(items=new_items))

        planned = standup.items.get(section=StandupItem.Section.PLANNED)
        self.assertEqual(planned.position, 7)

    def test_meetings_remain_optional(self):
        standup = self._create()

        # _valid_items() has no MEETING-section item.
        update_standup(standup=standup, validated_data=self._validated_data())

        self.assertFalse(standup.items.filter(section=StandupItem.Section.MEETING).exists())

    def test_blockers_update_correctly(self):
        standup = self._create(blockers="Old blocker.")

        updated = update_standup(
            standup=standup,
            validated_data=self._validated_data(blockers="New blocker."),
        )

        updated.refresh_from_db()
        self.assertEqual(updated.blockers, "New blocker.")

    def test_updating_to_a_duplicate_standup_date_is_rejected(self):
        self._create(standup_date=datetime.date(2026, 7, 13))
        other_standup = self._create(standup_date=datetime.date(2026, 7, 14))

        with self.assertRaises(IntegrityError):
            update_standup(
                standup=other_standup,
                validated_data=self._validated_data(standup_date=datetime.date(2026, 7, 13)),
            )

    def test_owner_cannot_be_changed(self):
        standup = self._create()
        other_user = User.objects.create_user(email="other@example.com", password="pw")

        validated_data = self._validated_data()
        validated_data["user"] = other_user  # should never be honored, even if present

        updated = update_standup(standup=standup, validated_data=validated_data)

        updated.refresh_from_db()
        self.assertEqual(updated.user, self.user)

    def test_rollback_when_item_update_fails(self):
        standup = self._create(blockers="Original blocker.")
        original_item_ids = set(standup.items.values_list("id", flat=True))

        items = _valid_items()
        items[1]["content"] = None  # violates the NOT NULL constraint on content

        with self.assertRaises(IntegrityError):
            update_standup(
                standup=standup,
                validated_data=self._validated_data(blockers="Attempted new blocker.", items=items),
            )

        standup.refresh_from_db()
        self.assertEqual(standup.blockers, "Original blocker.")
        self.assertEqual(set(standup.items.values_list("id", flat=True)), original_item_ids)
