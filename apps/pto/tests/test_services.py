import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.pto.models import PTOEntry
from apps.pto.services import create_pto_entry, delete_pto_entry, update_pto_entry


class CreatePTOEntryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")

    def _validated_data(self, **overrides):
        data = {
            "user": self.user,
            "start_date": datetime.date(2026, 7, 13),
            "end_date": datetime.date(2026, 7, 17),
            "reason": "Family vacation.",
            "handover_url": "https://example.com/handover",
        }
        data.update(overrides)
        return data

    def test_valid_pto_entry_is_created(self):
        entry = create_pto_entry(created_by=self.creator, validated_data=self._validated_data())

        self.assertEqual(PTOEntry.objects.count(), 1)
        self.assertEqual(entry.user, self.user)

    def test_authenticated_user_is_assigned_as_created_by(self):
        entry = create_pto_entry(created_by=self.creator, validated_data=self._validated_data())

        self.assertEqual(entry.created_by, self.creator)

    def test_pto_can_be_created_for_another_user(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        entry = create_pto_entry(
            created_by=self.creator, validated_data=self._validated_data(user=other)
        )

        self.assertEqual(entry.user, other)
        self.assertEqual(entry.created_by, self.creator)

    def test_request_data_cannot_override_created_by(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        data = self._validated_data()
        data["created_by"] = other

        entry = create_pto_entry(created_by=self.creator, validated_data=data)

        self.assertEqual(entry.created_by, self.creator)

    def test_service_returns_the_created_entry(self):
        entry = create_pto_entry(created_by=self.creator, validated_data=self._validated_data())

        self.assertIsInstance(entry, PTOEntry)
        self.assertIsNotNone(entry.pk)


class UpdatePTOEntryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")
        self.entry = create_pto_entry(
            created_by=self.creator,
            validated_data={
                "user": self.user,
                "start_date": datetime.date(2026, 7, 13),
                "end_date": datetime.date(2026, 7, 17),
                "reason": "Original reason.",
                "handover_url": "",
            },
        )

    def test_editable_fields_can_be_updated(self):
        new_start = datetime.date(2026, 7, 20)
        new_end = datetime.date(2026, 7, 24)

        updated = update_pto_entry(
            entry=self.entry,
            validated_data={
                "start_date": new_start,
                "end_date": new_end,
                "reason": "New reason.",
                "handover_url": "https://example.com/new",
            },
        )

        updated.refresh_from_db()
        self.assertEqual(updated.start_date, new_start)
        self.assertEqual(updated.end_date, new_end)
        self.assertEqual(updated.reason, "New reason.")
        self.assertEqual(updated.handover_url, "https://example.com/new")

    def test_created_by_remains_unchanged(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        updated = update_pto_entry(
            entry=self.entry, validated_data={"reason": "New reason.", "created_by": other}
        )

        updated.refresh_from_db()
        self.assertEqual(updated.created_by, self.creator)

    def test_invalid_data_does_not_partially_update_the_entry(self):
        original_reason = self.entry.reason

        with self.assertRaises(IntegrityError):
            # start_date=None violates the NOT NULL constraint at save().
            update_pto_entry(
                entry=self.entry,
                validated_data={"start_date": None, "reason": "Attempted."},
            )

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.reason, original_reason)

    def test_service_returns_the_updated_entry(self):
        updated = update_pto_entry(entry=self.entry, validated_data={"reason": "New reason."})

        self.assertIsInstance(updated, PTOEntry)
        self.assertEqual(updated.reason, "New reason.")


class DeletePTOEntryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")

    def _create(self, **overrides):
        data = {
            "user": self.user,
            "start_date": datetime.date(2026, 7, 13),
            "end_date": datetime.date(2026, 7, 17),
        }
        data.update(overrides)
        return create_pto_entry(created_by=self.creator, validated_data=data)

    def test_entry_is_removed(self):
        entry = self._create()
        entry_id = entry.id

        delete_pto_entry(entry=entry)

        self.assertFalse(PTOEntry.objects.filter(id=entry_id).exists())

    def test_deleting_one_entry_does_not_affect_others(self):
        entry = self._create()
        other_entry = self._create(
            start_date=datetime.date(2026, 8, 1), end_date=datetime.date(2026, 8, 3)
        )

        delete_pto_entry(entry=entry)

        self.assertTrue(PTOEntry.objects.filter(id=other_entry.id).exists())
