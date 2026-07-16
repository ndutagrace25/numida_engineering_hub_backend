import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.aob.models import AOBItem
from apps.aob.services import create_aob_item, update_aob_item

MONDAY = datetime.date(2026, 7, 13)


class CreateAOBItemServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def _validated_data(self, **overrides):
        data = {
            "title": "Office move",
            "description": "We're moving floors next month.",
            "external_url": "https://example.com/office-move",
            "week_start": MONDAY,
            "position": 1,
        }
        data.update(overrides)
        return data

    def test_valid_aob_item_is_created_successfully(self):
        item = create_aob_item(user=self.user, validated_data=self._validated_data())

        self.assertEqual(AOBItem.objects.count(), 1)
        self.assertEqual(item.title, "Office move")

    def test_authenticated_user_is_assigned_as_created_by(self):
        item = create_aob_item(user=self.user, validated_data=self._validated_data())

        self.assertEqual(item.created_by, self.user)

    def test_optional_description_can_be_blank(self):
        item = create_aob_item(user=self.user, validated_data=self._validated_data(description=""))

        self.assertEqual(item.description, "")

    def test_optional_external_url_can_be_omitted(self):
        data = self._validated_data()
        del data["external_url"]

        item = create_aob_item(user=self.user, validated_data=data)

        self.assertEqual(item.external_url, "")

    def test_week_start_and_position_are_saved_correctly(self):
        item = create_aob_item(
            user=self.user, validated_data=self._validated_data(week_start=MONDAY, position=3)
        )

        self.assertEqual(item.week_start, MONDAY)
        self.assertEqual(item.position, 3)

    def test_service_returns_the_created_aob_item_instance(self):
        item = create_aob_item(user=self.user, validated_data=self._validated_data())

        self.assertIsInstance(item, AOBItem)
        self.assertIsNotNone(item.pk)

    def test_request_data_cannot_override_created_by(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        data = self._validated_data()
        data["created_by"] = other  # should never be honored, even if present

        item = create_aob_item(user=self.user, validated_data=data)

        self.assertEqual(item.created_by, self.user)


class UpdateAOBItemServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.item = create_aob_item(
            user=self.user,
            validated_data={
                "title": "Office move",
                "description": "Original description.",
                "external_url": "https://example.com/original",
                "week_start": MONDAY,
                "position": 1,
            },
        )

    def test_all_editable_fields_can_be_updated(self):
        new_week = datetime.date(2026, 7, 20)

        updated = update_aob_item(
            item=self.item,
            validated_data={
                "title": "New title",
                "description": "New description.",
                "external_url": "https://example.com/new",
                "week_start": new_week,
                "position": 5,
            },
        )

        updated.refresh_from_db()
        self.assertEqual(updated.title, "New title")
        self.assertEqual(updated.description, "New description.")
        self.assertEqual(updated.external_url, "https://example.com/new")
        self.assertEqual(updated.week_start, new_week)
        self.assertEqual(updated.position, 5)

    def test_optional_description_can_be_cleared(self):
        updated = update_aob_item(item=self.item, validated_data={"description": ""})

        updated.refresh_from_db()
        self.assertEqual(updated.description, "")

    def test_optional_external_url_can_be_cleared(self):
        updated = update_aob_item(item=self.item, validated_data={"external_url": ""})

        updated.refresh_from_db()
        self.assertEqual(updated.external_url, "")

    def test_created_by_remains_unchanged(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        updated = update_aob_item(
            item=self.item,
            validated_data={"title": "New title", "created_by": other},
        )

        updated.refresh_from_db()
        self.assertEqual(updated.created_by, self.user)

    def test_invalid_data_does_not_partially_update_the_item(self):
        original_title = self.item.title
        original_position = self.item.position

        with self.assertRaises(IntegrityError):
            # title=None violates the NOT NULL constraint at save() time.
            update_aob_item(item=self.item, validated_data={"title": None, "position": 99})

        self.item.refresh_from_db()
        self.assertEqual(self.item.title, original_title)
        self.assertEqual(self.item.position, original_position)

    def test_service_returns_the_updated_aob_item_instance(self):
        updated = update_aob_item(item=self.item, validated_data={"title": "New title"})

        self.assertIsInstance(updated, AOBItem)
        self.assertEqual(updated.title, "New title")
