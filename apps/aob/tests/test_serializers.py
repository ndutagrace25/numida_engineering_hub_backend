import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.aob.models import AOBItem
from apps.aob.serializers import AOBItemSerializer

MONDAY = datetime.date(2026, 7, 13)


def _valid_payload(**overrides):
    data = {
        "title": "Office move",
        "description": "We're moving floors next month.",
        "external_url": "https://example.com/office-move",
        "week_start": MONDAY.isoformat(),
        "position": 1,
    }
    data.update(overrides)
    return data


class AOBItemSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )

    def test_valid_data_passes_validation(self):
        serializer = AOBItemSerializer(data=_valid_payload())

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_blank_title_is_rejected(self):
        serializer = AOBItemSerializer(data=_valid_payload(title="   "))

        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_description_is_optional(self):
        payload = _valid_payload()
        del payload["description"]

        serializer = AOBItemSerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_external_url_is_optional(self):
        payload = _valid_payload()
        del payload["external_url"]

        serializer = AOBItemSerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_http_urls_are_rejected(self):
        serializer = AOBItemSerializer(
            data=_valid_payload(external_url="http://example.com/office-move")
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("external_url", serializer.errors)

    def test_https_urls_are_accepted(self):
        serializer = AOBItemSerializer(
            data=_valid_payload(external_url="https://example.com/office-move")
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_non_monday_week_start_is_rejected(self):
        serializer = AOBItemSerializer(data=_valid_payload(week_start="2026-07-14"))  # Tuesday

        self.assertFalse(serializer.is_valid())
        self.assertIn("week_start", serializer.errors)

    def test_negative_position_is_rejected(self):
        serializer = AOBItemSerializer(data=_valid_payload(position=-1))

        self.assertFalse(serializer.is_valid())
        self.assertIn("position", serializer.errors)

    def test_zero_position_is_accepted(self):
        serializer = AOBItemSerializer(data=_valid_payload(position=0))

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_created_by_is_read_only(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        serializer = AOBItemSerializer(data=_valid_payload(created_by=other.id))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("created_by", serializer.validated_data)

    def test_sensitive_user_fields_are_not_exposed(self):
        item = AOBItem.objects.create(
            title="Office move", week_start=MONDAY, position=1, created_by=self.user
        )

        data = AOBItemSerializer(item).data

        creator = data["created_by"]
        self.assertNotIn("email", creator)
        self.assertNotIn("password", creator)
        self.assertNotIn("is_active", creator)
        self.assertNotIn("is_staff", creator)
        self.assertNotIn("is_superuser", creator)

    def test_serialized_output_contains_expected_fields(self):
        item = AOBItem.objects.create(
            title="Office move",
            description="Details.",
            external_url="https://example.com",
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        data = AOBItemSerializer(item).data

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "title",
                "description",
                "external_url",
                "week_start",
                "position",
                "created_by",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(
            set(data["created_by"].keys()), {"id", "first_name", "last_name", "display_name"}
        )
        self.assertEqual(data["created_by"]["display_name"], "Jane Doe")
