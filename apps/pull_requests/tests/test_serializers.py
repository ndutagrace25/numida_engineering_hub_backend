import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.serializers import PullRequestLinkSerializer

MONDAY = datetime.date(2026, 7, 13)


def _valid_payload(**overrides):
    data = {
        "title": "Fix login bug",
        "url": "https://github.com/org/repo/pull/6905",
        "group_name": "App 3.0 PRs",
        "status": "OPEN",
        "week_start": MONDAY.isoformat(),
        "position": 1,
    }
    data.update(overrides)
    return data


class PullRequestLinkSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )

    def test_valid_data_passes_validation(self):
        serializer = PullRequestLinkSerializer(data=_valid_payload())

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_http_urls_are_rejected(self):
        serializer = PullRequestLinkSerializer(
            data=_valid_payload(url="http://github.com/org/repo/pull/6905")
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("url", serializer.errors)

    def test_https_urls_are_accepted(self):
        serializer = PullRequestLinkSerializer(
            data=_valid_payload(url="https://github.com/org/repo/pull/6905")
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_non_monday_week_start_is_rejected(self):
        serializer = PullRequestLinkSerializer(data=_valid_payload(week_start="2026-07-14"))

        self.assertFalse(serializer.is_valid())
        self.assertIn("week_start", serializer.errors)

    def test_invalid_status_is_rejected(self):
        serializer = PullRequestLinkSerializer(data=_valid_payload(status="NOT_A_STATUS"))

        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)

    def test_negative_position_is_rejected(self):
        serializer = PullRequestLinkSerializer(data=_valid_payload(position=-1))

        self.assertFalse(serializer.is_valid())
        self.assertIn("position", serializer.errors)

    def test_zero_position_is_accepted(self):
        serializer = PullRequestLinkSerializer(data=_valid_payload(position=0))

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_created_by_is_read_only(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        serializer = PullRequestLinkSerializer(data=_valid_payload(created_by=other.id))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("created_by", serializer.validated_data)

    def test_sensitive_creator_fields_are_not_exposed(self):
        link = PullRequestLink.objects.create(
            title="Fix login bug",
            url="https://github.com/org/repo/pull/6905",
            group_name="App 3.0 PRs",
            status=PullRequestLink.Status.OPEN,
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        data = PullRequestLinkSerializer(link).data

        creator = data["created_by"]
        self.assertNotIn("email", creator)
        self.assertNotIn("password", creator)
        self.assertNotIn("is_active", creator)
        self.assertNotIn("is_staff", creator)

    def test_serialized_output_contains_expected_fields(self):
        link = PullRequestLink.objects.create(
            title="Fix login bug",
            url="https://github.com/org/repo/pull/6905",
            group_name="App 3.0 PRs",
            status=PullRequestLink.Status.OPEN,
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        data = PullRequestLinkSerializer(link).data

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "title",
                "url",
                "group_name",
                "status",
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
