import datetime

from apps.accounts.models import User
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.services import create_pull_request_link
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


class PullRequestLinkListViewTests(BaseAPITestCase):
    url = "/api/v1/pull-request-links/"

    def setUp(self):
        self.grace = User.objects.create_user(
            email="grace@example.com", password="pw", first_name="Grace", last_name="Nduta"
        )
        self.amina = User.objects.create_user(
            email="amina@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )
        self.authenticate(self.grace)

        self.grace_link = create_pull_request_link(
            created_by=self.grace,
            validated_data={
                "title": "Fix login bug",
                "url": "https://github.com/org/repo/pull/6905",
                "group_name": "App 3.0 PRs",
                "status": PullRequestLink.Status.IN_REVIEW,
                "week_start": MONDAY,
                "position": 1,
            },
        )
        self.amina_link = create_pull_request_link(
            created_by=self.amina,
            validated_data={
                "title": "Add search endpoint",
                "url": "https://github.com/org/repo/pull/7100",
                "group_name": "Platform PRs",
                "status": PullRequestLink.Status.APPROVED,
                "week_start": MONDAY + datetime.timedelta(days=7),
                "position": 1,
            },
        )

    def _ids(self, response):
        return [row["id"] for row in self.get_data(response)["results"]]

    def test_any_authenticated_user_can_view_the_list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_default_ordering_works(self):
        response = self.client.get(self.url)

        self.assertEqual(self._ids(response), [self.amina_link.id, self.grace_link.id])

    def test_pagination_works(self):
        response = self.client.get(self.url, {"page_size": 1})

        data = self.get_data(response)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["count"], 2)
        self.assertIsNotNone(data["next"])

    def test_filtering_by_week_works(self):
        response = self.client.get(self.url, {"week_start": MONDAY.isoformat()})

        self.assertEqual(self._ids(response), [self.grace_link.id])

    def test_filtering_by_week_range_works(self):
        response = self.client.get(
            self.url, {"week_after": "2026-07-15", "week_before": "2026-07-31"}
        )

        self.assertEqual(self._ids(response), [self.amina_link.id])

    def test_filtering_by_status_works(self):
        response = self.client.get(self.url, {"status": "APPROVED"})

        self.assertEqual(self._ids(response), [self.amina_link.id])

    def test_filtering_by_group_name_works(self):
        response = self.client.get(self.url, {"group_name": "App 3.0 PRs"})

        self.assertEqual(self._ids(response), [self.grace_link.id])

    def test_filtering_by_creator_works(self):
        response = self.client.get(self.url, {"created_by": self.amina.id})

        self.assertEqual(self._ids(response), [self.amina_link.id])

    def test_search_by_title_works(self):
        response = self.client.get(self.url, {"search": "search endpoint"})

        self.assertEqual(self._ids(response), [self.amina_link.id])

    def test_search_by_group_name_works(self):
        response = self.client.get(self.url, {"search": "Platform"})

        self.assertEqual(self._ids(response), [self.amina_link.id])

    def test_search_by_creator_name_works(self):
        response = self.client.get(self.url, {"search": "Grace"})

        self.assertEqual(self._ids(response), [self.grace_link.id])

    def test_search_by_url_or_pr_number_works(self):
        response = self.client.get(self.url, {"search": "6905"})

        self.assertEqual(self._ids(response), [self.grace_link.id])

    def test_multiple_filters_can_be_combined(self):
        response = self.client.get(
            self.url, {"status": "IN_REVIEW", "week_start": MONDAY.isoformat()}
        )

        self.assertEqual(self._ids(response), [self.grace_link.id])

    def test_combined_filters_returning_nothing(self):
        response = self.client.get(
            self.url, {"status": "APPROVED", "week_start": MONDAY.isoformat()}
        )

        self.assertEqual(self._ids(response), [])

    def test_empty_results_return_valid_empty_paginated_response(self):
        response = self.client.get(self.url, {"search": "nonexistent-keyword-xyz"})

        data = self.get_data(response)
        self.assertEqual(data["results"], [])
        self.assertEqual(data["count"], 0)

    def test_sensitive_creator_fields_are_not_exposed(self):
        response = self.client.get(self.url)

        for row in self.get_data(response)["results"]:
            creator = row["created_by"]
            self.assertNotIn("email", creator)
            self.assertNotIn("password", creator)
            self.assertNotIn("is_active", creator)

    def test_invalid_filter_value_uses_standard_error_format(self):
        response = self.client.get(self.url, {"created_by": "not-a-number"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_error(response)["code"], "VALIDATION_ERROR")

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_query_count_does_not_grow_with_more_data(self):
        # Paginator count + select_related(created_by) main query. setUp()
        # already created 2 links.
        with self.assertNumQueries(2):
            self.client.get(self.url)

        for i in range(5):
            create_pull_request_link(
                created_by=self.grace,
                validated_data={
                    "title": f"Extra PR {i}",
                    "url": f"https://github.com/org/repo/pull/{7000 + i}",
                    "group_name": "App 3.0 PRs",
                    "status": PullRequestLink.Status.OPEN,
                    "week_start": MONDAY,
                    "position": i + 2,
                },
            )

        with self.assertNumQueries(2):
            self.client.get(self.url)
