import datetime

from django.http import Http404
from django.test import TestCase

from apps.accounts.models import User
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.selectors import get_pull_request_link_by_id, list_pull_request_links
from apps.pull_requests.services import create_pull_request_link

MONDAY = datetime.date(2026, 7, 13)


def _valid_data(**overrides):
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


class GetPullRequestLinkByIdSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.link = create_pull_request_link(created_by=self.user, validated_data=_valid_data())

    def test_returns_the_correct_link(self):
        result = get_pull_request_link_by_id(self.link.id)

        self.assertEqual(result.id, self.link.id)

    def test_raises_404_for_nonexistent_link(self):
        with self.assertRaises(Http404):
            get_pull_request_link_by_id(999999)


class ListPullRequestLinksSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")

    def test_returns_all_links(self):
        create_pull_request_link(created_by=self.user, validated_data=_valid_data(title="A"))
        create_pull_request_link(created_by=self.user, validated_data=_valid_data(title="B"))

        self.assertEqual(len(list(list_pull_request_links())), 2)

    def test_ordered_by_week_start_desc_group_name_asc_position_asc(self):
        older_week = create_pull_request_link(
            created_by=self.user,
            validated_data=_valid_data(title="Old", week_start=datetime.date(2026, 7, 6)),
        )
        newer_week_group_b = create_pull_request_link(
            created_by=self.user,
            validated_data=_valid_data(
                title="NewB", group_name="Team B", week_start=MONDAY, position=1
            ),
        )
        newer_week_group_a = create_pull_request_link(
            created_by=self.user,
            validated_data=_valid_data(
                title="NewA", group_name="Team A", week_start=MONDAY, position=1
            ),
        )

        ids = [link.id for link in list_pull_request_links()]

        self.assertEqual(ids, [newer_week_group_a.id, newer_week_group_b.id, older_week.id])

    def test_empty_database_returns_empty_queryset(self):
        self.assertEqual(list(list_pull_request_links()), [])

    def test_avoids_unnecessary_database_queries(self):
        for i in range(3):
            create_pull_request_link(
                created_by=self.user, validated_data=_valid_data(title=f"Item {i}")
            )

        with self.assertNumQueries(1):
            links = list(list_pull_request_links())
            for link in links:
                _ = link.created_by.email
