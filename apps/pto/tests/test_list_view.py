import datetime

from apps.accounts.models import User
from apps.pto.services import create_pto_entry
from tests.base import BaseAPITestCase


class PTOEntryListViewTests(BaseAPITestCase):
    url = "/api/v1/pto/"

    def setUp(self):
        self.grace = User.objects.create_user(
            email="grace@example.com", password="pw", first_name="Grace", last_name="Nduta"
        )
        self.amina = User.objects.create_user(
            email="amina@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")
        self.authenticate(self.creator)

        self.grace_entry = create_pto_entry(
            created_by=self.creator,
            validated_data={
                "user": self.grace,
                "start_date": datetime.date(2026, 7, 13),
                "end_date": datetime.date(2026, 7, 17),
                "reason": "Annual leave.",
            },
        )
        # created_by intentionally different from user, to distinguish
        # "who the PTO is for" from "who logged it" in filter tests.
        self.amina_entry = create_pto_entry(
            created_by=self.grace,
            validated_data={
                "user": self.amina,
                "start_date": datetime.date(2026, 8, 1),
                "end_date": datetime.date(2026, 8, 5),
                "reason": "Sick leave.",
            },
        )

    def _ids(self, response):
        return [row["id"] for row in self.get_data(response)["results"]]

    def test_any_authenticated_user_can_view_the_list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_default_ordering_works(self):
        response = self.client.get(self.url)

        self.assertEqual(self._ids(response), [self.grace_entry.id, self.amina_entry.id])

    def test_pagination_works(self):
        response = self.client.get(self.url, {"page_size": 1})

        data = self.get_data(response)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["count"], 2)
        self.assertIsNotNone(data["next"])

    def test_filtering_by_user_works(self):
        response = self.client.get(self.url, {"user": self.amina.id})

        self.assertEqual(self._ids(response), [self.amina_entry.id])

    def test_filtering_by_created_by_works(self):
        response = self.client.get(self.url, {"created_by": self.grace.id})

        self.assertEqual(self._ids(response), [self.amina_entry.id])

    def test_filtering_by_exact_dates_works(self):
        response = self.client.get(self.url, {"start_date": "2026-07-13"})

        self.assertEqual(self._ids(response), [self.grace_entry.id])

    def test_filtering_by_date_range_works(self):
        response = self.client.get(
            self.url, {"date_after": "2026-07-20", "date_before": "2026-08-10"}
        )

        self.assertEqual(self._ids(response), [self.amina_entry.id])

    def test_active_on_returns_entries_covering_that_date(self):
        response = self.client.get(self.url, {"active_on": "2026-07-15"})

        self.assertEqual(self._ids(response), [self.grace_entry.id])

    def test_search_by_user_name_works(self):
        response = self.client.get(self.url, {"search": "Amina"})

        self.assertEqual(self._ids(response), [self.amina_entry.id])

    def test_search_by_reason_works(self):
        response = self.client.get(self.url, {"search": "Annual"})

        self.assertEqual(self._ids(response), [self.grace_entry.id])

    def test_multiple_filters_can_be_combined(self):
        response = self.client.get(self.url, {"user": self.grace.id, "start_date": "2026-07-13"})

        self.assertEqual(self._ids(response), [self.grace_entry.id])

    def test_combined_filters_returning_nothing(self):
        response = self.client.get(self.url, {"user": self.amina.id, "start_date": "2026-07-13"})

        self.assertEqual(self._ids(response), [])

    def test_empty_results_return_valid_empty_paginated_response(self):
        response = self.client.get(self.url, {"search": "nonexistent-keyword-xyz"})

        data = self.get_data(response)
        self.assertEqual(data["results"], [])
        self.assertEqual(data["count"], 0)

    def test_sensitive_user_fields_are_not_exposed(self):
        response = self.client.get(self.url)

        for row in self.get_data(response)["results"]:
            for key in ("user", "created_by"):
                self.assertNotIn("email", row[key])
                self.assertNotIn("password", row[key])
                self.assertNotIn("is_active", row[key])

    def test_invalid_filter_value_uses_standard_error_format(self):
        response = self.client.get(self.url, {"user": "not-a-number"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_error(response)["code"], "VALIDATION_ERROR")

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_query_count_does_not_grow_with_more_data(self):
        # Paginator count + select_related(user, created_by) main query.
        # setUp() already created 2 entries.
        with self.assertNumQueries(2):
            self.client.get(self.url)

        for offset in range(5):
            create_pto_entry(
                created_by=self.creator,
                validated_data={
                    "user": self.grace,
                    "start_date": datetime.date(2026, 9, 1) + datetime.timedelta(days=offset * 10),
                    "end_date": datetime.date(2026, 9, 3) + datetime.timedelta(days=offset * 10),
                    "reason": "",
                },
            )

        with self.assertNumQueries(2):
            self.client.get(self.url)
