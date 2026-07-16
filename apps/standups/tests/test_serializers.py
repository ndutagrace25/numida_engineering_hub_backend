import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.standups.models import Standup, StandupItem
from apps.standups.serializers import StandupItemSerializer, StandupSerializer


def _valid_items_payload():
    return [
        {"section": "COMPLETED", "content": "Shipped the login endpoint.", "position": 1},
        {"section": "CURRENT", "content": "Working on the standups API.", "position": 1},
        {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 1},
    ]


class StandupItemSerializerTests(TestCase):
    def test_valid_item_passes_validation(self):
        serializer = StandupItemSerializer(
            data={"section": "COMPLETED", "content": "Shipped X.", "position": 1}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_blank_content_is_rejected(self):
        serializer = StandupItemSerializer(
            data={"section": "COMPLETED", "content": "   ", "position": 1}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)

    def test_invalid_section_is_rejected(self):
        serializer = StandupItemSerializer(
            data={"section": "NOT_A_SECTION", "content": "Something.", "position": 1}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("section", serializer.errors)

    def test_id_created_at_updated_at_are_read_only(self):
        serializer = StandupItemSerializer(
            data={
                "id": 999,
                "section": "COMPLETED",
                "content": "Shipped X.",
                "position": 1,
                "created_at": "2000-01-01T00:00:00Z",
                "updated_at": "2000-01-01T00:00:00Z",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        for field in ("id", "created_at", "updated_at"):
            self.assertNotIn(field, serializer.validated_data)


class StandupSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def _payload(self, items=None, **overrides):
        data = {
            "standup_date": "2026-07-13",
            "blockers": "",
            "items": _valid_items_payload() if items is None else items,
        }
        data.update(overrides)
        return data

    def test_valid_standup_data_passes_validation(self):
        serializer = StandupSerializer(data=self._payload())

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_completed_items_is_rejected(self):
        items = [item for item in _valid_items_payload() if item["section"] != "COMPLETED"]

        serializer = StandupSerializer(data=self._payload(items=items))

        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_missing_current_items_is_rejected(self):
        items = [item for item in _valid_items_payload() if item["section"] != "CURRENT"]

        serializer = StandupSerializer(data=self._payload(items=items))

        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_missing_planned_items_is_rejected(self):
        items = [item for item in _valid_items_payload() if item["section"] != "PLANNED"]

        serializer = StandupSerializer(data=self._payload(items=items))

        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_missing_meeting_items_is_allowed(self):
        serializer = StandupSerializer(data=self._payload())  # no MEETING items included

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_blank_item_content_is_rejected(self):
        items = _valid_items_payload()
        items[0]["content"] = "   "

        serializer = StandupSerializer(data=self._payload(items=items))

        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_invalid_section_is_rejected(self):
        items = _valid_items_payload()
        items[0]["section"] = "NOT_A_SECTION"

        serializer = StandupSerializer(data=self._payload(items=items))

        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_duplicate_positions_within_same_section_is_rejected(self):
        items = _valid_items_payload()
        items.append({"section": "COMPLETED", "content": "Another one.", "position": 1})

        serializer = StandupSerializer(data=self._payload(items=items))

        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_duplicate_position_across_different_sections_is_allowed(self):
        # position=1 already used by COMPLETED/CURRENT/PLANNED in the base
        # payload; only *within* a section must positions be unique.
        serializer = StandupSerializer(data=self._payload())

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_user_field_is_read_only(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        serializer = StandupSerializer(data=self._payload(user=other.id))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("user", serializer.validated_data)

    def test_read_only_fields_cannot_be_changed_through_input(self):
        serializer = StandupSerializer(
            data=self._payload(
                id=999,
                created_at="2000-01-01T00:00:00Z",
                updated_at="2000-01-01T00:00:00Z",
            )
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        for field in ("id", "created_at", "updated_at"):
            self.assertNotIn(field, serializer.validated_data)

    def test_serialized_output_contains_nested_items(self):
        standup = Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))
        StandupItem.objects.create(
            standup=standup, section=StandupItem.Section.COMPLETED, content="Done.", position=1
        )
        StandupItem.objects.create(
            standup=standup, section=StandupItem.Section.CURRENT, content="Doing.", position=1
        )

        data = StandupSerializer(standup).data

        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["user"]["email"], "jane@example.com")

    def test_partial_update_without_items_does_not_require_sections(self):
        standup = Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))
        StandupItem.objects.create(
            standup=standup, section=StandupItem.Section.COMPLETED, content="Done.", position=1
        )

        serializer = StandupSerializer(standup, data={"blockers": "New blocker."}, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("items", serializer.validated_data)

    def test_partial_update_with_items_still_requires_sections(self):
        standup = Standup.objects.create(user=self.user, standup_date=datetime.date(2026, 7, 13))

        serializer = StandupSerializer(
            standup,
            data={"items": [{"section": "COMPLETED", "content": "Done.", "position": 1}]},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)
