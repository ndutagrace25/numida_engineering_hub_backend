import datetime

from apps.accounts.models import User
from apps.aob.services import create_aob_item
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


class AOBItemListViewTests(BaseAPITestCase):
    url = "/api/v1/aob-items/"

    def setUp(self):
        self.grace = User.objects.create_user(
            email="grace@example.com", password="pw", first_name="Grace", last_name="Nduta"
        )
        self.amina = User.objects.create_user(
            email="amina@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )
        self.authenticate(self.grace)

        self.grace_item = create_aob_item(
            user=self.grace,
            validated_data={
                "title": "Office move",
                "description": "We're moving floors next month.",
                "external_url": "",
                "week_start": MONDAY,
                "position": 1,
            },
        )
        self.amina_item = create_aob_item(
            user=self.amina,
            validated_data={
                "title": "New deployment process",
                "description": "Rolling out a new CI/CD pipeline.",
                "external_url": "",
                "week_start": MONDAY + datetime.timedelta(days=7),
                "position": 1,
            },
        )

    def _ids(self, response):
        return [row["id"] for row in self.get_data(response)["results"]]

    def test_authenticated_users_can_retrieve_the_list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_items_from_different_users_are_returned(self):
        response = self.client.get(self.url)

        creator_ids = {row["created_by"]["id"] for row in self.get_data(response)["results"]}
        self.assertEqual(creator_ids, {self.grace.id, self.amina.id})

    def test_default_ordering_works(self):
        response = self.client.get(self.url)

        self.assertEqual(self._ids(response), [self.amina_item.id, self.grace_item.id])

    def test_pagination_works(self):
        response = self.client.get(self.url, {"page_size": 1})

        data = self.get_data(response)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["count"], 2)
        self.assertIsNotNone(data["next"])

    def test_filtering_by_exact_week_start_works(self):
        response = self.client.get(self.url, {"week_start": MONDAY.isoformat()})

        self.assertEqual(self._ids(response), [self.grace_item.id])

    def test_filtering_by_week_range_works(self):
        response = self.client.get(
            self.url, {"week_after": "2026-07-15", "week_before": "2026-07-31"}
        )

        self.assertEqual(self._ids(response), [self.amina_item.id])

    def test_filtering_by_created_by_works(self):
        response = self.client.get(self.url, {"created_by": self.grace.id})

        self.assertEqual(self._ids(response), [self.grace_item.id])

    def test_search_by_title_works(self):
        response = self.client.get(self.url, {"search": "deployment"})

        self.assertEqual(self._ids(response), [self.amina_item.id])

    def test_search_by_description_works(self):
        response = self.client.get(self.url, {"search": "moving floors"})

        self.assertEqual(self._ids(response), [self.grace_item.id])

    def test_search_by_creator_first_name_works(self):
        response = self.client.get(self.url, {"search": "Amina"})

        self.assertEqual(self._ids(response), [self.amina_item.id])

    def test_search_by_creator_last_name_works(self):
        response = self.client.get(self.url, {"search": "Nduta"})

        self.assertEqual(self._ids(response), [self.grace_item.id])

    def test_multiple_filters_can_be_combined(self):
        response = self.client.get(
            self.url, {"created_by": self.grace.id, "week_start": MONDAY.isoformat()}
        )

        self.assertEqual(self._ids(response), [self.grace_item.id])

    def test_combined_filters_returning_nothing(self):
        response = self.client.get(
            self.url, {"created_by": self.amina.id, "week_start": MONDAY.isoformat()}
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
            self.assertNotIn("is_staff", creator)
            self.assertNotIn("is_superuser", creator)

    def test_invalid_filter_value_uses_standard_error_format(self):
        response = self.client.get(self.url, {"created_by": "not-a-number"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_error(response)["code"], "VALIDATION_ERROR")

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
