import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.pull_requests.models import PullRequestLink

MONDAY = datetime.date(2026, 7, 13)


class PullRequestLinkModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def test_valid_pr_link_can_be_created(self):
        link = PullRequestLink.objects.create(
            title="Fix login bug",
            url="https://github.com/org/repo/pull/6905",
            group_name="App 3.0 PRs",
            status=PullRequestLink.Status.OPEN,
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        self.assertEqual(link.title, "Fix login bug")
        self.assertEqual(link.created_by, self.user)

    def test_non_monday_week_start_is_rejected_through_model_validation(self):
        link = PullRequestLink(
            title="Fix login bug",
            url="https://github.com/org/repo/pull/6905",
            group_name="App 3.0 PRs",
            status=PullRequestLink.Status.OPEN,
            week_start=datetime.date(2026, 7, 14),  # a Tuesday
            position=1,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            link.full_clean()

    def test_http_url_is_rejected_through_model_validation(self):
        link = PullRequestLink(
            title="Fix login bug",
            url="http://github.com/org/repo/pull/6905",
            group_name="App 3.0 PRs",
            status=PullRequestLink.Status.OPEN,
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            link.full_clean()

    def test_ordering_works_correctly(self):
        older_week = PullRequestLink.objects.create(
            title="A",
            url="https://example.com/1",
            group_name="Team A",
            status=PullRequestLink.Status.OPEN,
            week_start=datetime.date(2026, 7, 6),
            position=1,
            created_by=self.user,
        )
        newer_week_group_b = PullRequestLink.objects.create(
            title="B",
            url="https://example.com/2",
            group_name="Team B",
            status=PullRequestLink.Status.OPEN,
            week_start=MONDAY,
            position=2,
            created_by=self.user,
        )
        newer_week_group_a = PullRequestLink.objects.create(
            title="C",
            url="https://example.com/3",
            group_name="Team A",
            status=PullRequestLink.Status.OPEN,
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        self.assertEqual(
            list(PullRequestLink.objects.all()),
            [newer_week_group_a, newer_week_group_b, older_week],
        )

    def test_string_representation_is_readable(self):
        link = PullRequestLink.objects.create(
            title="Fix login bug",
            url="https://github.com/org/repo/pull/6905",
            group_name="App 3.0 PRs",
            status=PullRequestLink.Status.IN_REVIEW,
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        self.assertEqual(str(link), f"Fix login bug (In review) — week of {MONDAY}")

    def test_deleting_a_creator_does_not_delete_historical_pr_link_records(self):
        link = PullRequestLink.objects.create(
            title="Fix login bug",
            url="https://github.com/org/repo/pull/6905",
            group_name="App 3.0 PRs",
            status=PullRequestLink.Status.OPEN,
            week_start=MONDAY,
            position=1,
            created_by=self.user,
        )

        self.user.delete()

        link.refresh_from_db()
        self.assertIsNone(link.created_by)
