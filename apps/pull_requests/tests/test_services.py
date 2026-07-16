import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.services import (
    create_pull_request_link,
    delete_pull_request_link,
    update_pull_request_link,
)

MONDAY = datetime.date(2026, 7, 13)


class CreatePullRequestLinkServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def _validated_data(self, **overrides):
        data = {
            "title": "Fix login bug",
            "url": "https://github.com/org/repo/pull/6905",
            "group_name": "App 3.0 PRs",
            "status": PullRequestLink.Status.OPEN,
            "week_start": MONDAY,
            "position": 1,
        }
        data.update(overrides)
        return data

    def test_valid_link_is_created(self):
        link = create_pull_request_link(created_by=self.user, validated_data=self._validated_data())

        self.assertEqual(PullRequestLink.objects.count(), 1)
        self.assertEqual(link.title, "Fix login bug")

    def test_authenticated_user_is_assigned_as_created_by(self):
        link = create_pull_request_link(created_by=self.user, validated_data=self._validated_data())

        self.assertEqual(link.created_by, self.user)

    def test_request_data_cannot_override_created_by(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        data = self._validated_data()
        data["created_by"] = other

        link = create_pull_request_link(created_by=self.user, validated_data=data)

        self.assertEqual(link.created_by, self.user)

    def test_service_returns_the_created_link(self):
        link = create_pull_request_link(created_by=self.user, validated_data=self._validated_data())

        self.assertIsInstance(link, PullRequestLink)
        self.assertIsNotNone(link.pk)


class UpdatePullRequestLinkServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.link = create_pull_request_link(
            created_by=self.user,
            validated_data={
                "title": "Fix login bug",
                "url": "https://github.com/org/repo/pull/6905",
                "group_name": "App 3.0 PRs",
                "status": PullRequestLink.Status.OPEN,
                "week_start": MONDAY,
                "position": 1,
            },
        )

    def test_editable_fields_can_be_updated(self):
        updated = update_pull_request_link(
            link=self.link,
            validated_data={"status": PullRequestLink.Status.APPROVED, "position": 3},
        )

        updated.refresh_from_db()
        self.assertEqual(updated.status, PullRequestLink.Status.APPROVED)
        self.assertEqual(updated.position, 3)

    def test_created_by_remains_unchanged(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        updated = update_pull_request_link(
            link=self.link, validated_data={"title": "New title", "created_by": other}
        )

        updated.refresh_from_db()
        self.assertEqual(updated.created_by, self.user)

    def test_invalid_data_does_not_partially_update_the_link(self):
        original_title = self.link.title

        with self.assertRaises(IntegrityError):
            # title=None violates the NOT NULL constraint at save() time.
            update_pull_request_link(link=self.link, validated_data={"title": None, "position": 99})

        self.link.refresh_from_db()
        self.assertEqual(self.link.title, original_title)
        self.assertNotEqual(self.link.position, 99)

    def test_service_returns_the_updated_link(self):
        updated = update_pull_request_link(link=self.link, validated_data={"title": "New title"})

        self.assertIsInstance(updated, PullRequestLink)
        self.assertEqual(updated.title, "New title")


class DeletePullRequestLinkServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def _create(self, **overrides):
        data = {
            "title": "Fix login bug",
            "url": "https://github.com/org/repo/pull/6905",
            "group_name": "App 3.0 PRs",
            "status": PullRequestLink.Status.OPEN,
            "week_start": MONDAY,
            "position": 1,
        }
        data.update(overrides)
        return create_pull_request_link(created_by=self.user, validated_data=data)

    def test_link_is_removed(self):
        link = self._create()
        link_id = link.id

        delete_pull_request_link(link=link)

        self.assertFalse(PullRequestLink.objects.filter(id=link_id).exists())

    def test_deleting_one_link_does_not_affect_others(self):
        link = self._create()
        other_link = self._create(title="Other", week_start=MONDAY + datetime.timedelta(days=7))

        delete_pull_request_link(link=link)

        self.assertTrue(PullRequestLink.objects.filter(id=other_link.id).exists())
