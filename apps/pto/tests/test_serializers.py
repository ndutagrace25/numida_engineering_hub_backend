import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.pto.models import PTOEntry
from apps.pto.serializers import PTOEntrySerializer


def _valid_payload(user_id, **overrides):
    data = {
        "user": user_id,
        "start_date": "2026-07-13",
        "end_date": "2026-07-17",
        "reason": "Family vacation.",
        "handover_url": "https://example.com/handover",
    }
    data.update(overrides)
    return data


class PTOEntrySerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")

    def test_valid_data_passes_validation(self):
        serializer = PTOEntrySerializer(data=_valid_payload(self.user.id))

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_end_date_before_start_date_is_rejected(self):
        serializer = PTOEntrySerializer(
            data=_valid_payload(self.user.id, start_date="2026-07-17", end_date="2026-07-13")
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)

    def test_one_day_pto_is_accepted(self):
        serializer = PTOEntrySerializer(
            data=_valid_payload(self.user.id, start_date="2026-07-13", end_date="2026-07-13")
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_reason_is_optional(self):
        payload = _valid_payload(self.user.id)
        del payload["reason"]

        serializer = PTOEntrySerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_handover_url_is_optional(self):
        payload = _valid_payload(self.user.id)
        del payload["handover_url"]

        serializer = PTOEntrySerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_http_handover_url_is_rejected(self):
        serializer = PTOEntrySerializer(
            data=_valid_payload(self.user.id, handover_url="http://example.com/handover")
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("handover_url", serializer.errors)

    def test_https_handover_url_is_accepted(self):
        serializer = PTOEntrySerializer(
            data=_valid_payload(self.user.id, handover_url="https://example.com/handover")
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_created_by_is_read_only(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        serializer = PTOEntrySerializer(data=_valid_payload(self.user.id, created_by=other.id))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("created_by", serializer.validated_data)

    def test_user_field_accepts_a_different_user(self):
        serializer = PTOEntrySerializer(data=_valid_payload(self.user.id))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["user"], self.user)

    def test_partial_update_validates_against_existing_instance_dates(self):
        entry = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 17),
            created_by=self.creator,
        )

        # Moving end_date earlier than the *existing* start_date should
        # still be rejected, even though start_date isn't in this request.
        serializer = PTOEntrySerializer(entry, data={"end_date": "2026-07-01"}, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)

    def test_output_contains_nested_user_and_created_by(self):
        entry = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 17),
            created_by=self.creator,
        )

        data = PTOEntrySerializer(entry).data

        self.assertEqual(
            set(data["user"].keys()), {"id", "first_name", "last_name", "display_name"}
        )
        self.assertEqual(
            set(data["created_by"].keys()), {"id", "first_name", "last_name", "display_name"}
        )
        self.assertEqual(data["user"]["display_name"], "Jane Doe")

    def test_sensitive_fields_are_not_exposed(self):
        entry = PTOEntry.objects.create(
            user=self.user,
            start_date=datetime.date(2026, 7, 13),
            end_date=datetime.date(2026, 7, 17),
            created_by=self.creator,
        )

        data = PTOEntrySerializer(entry).data

        for key in ("user", "created_by"):
            self.assertNotIn("email", data[key])
            self.assertNotIn("password", data[key])
            self.assertNotIn("is_active", data[key])
            self.assertNotIn("is_staff", data[key])
