import datetime

from apps.accounts.models import User
from apps.standups.services import create_standup
from tests.base import BaseAPITestCase


class StandupListFilteringTests(BaseAPITestCase):
    url = "/api/v1/standups/"

    def setUp(self):
        self.grace = User.objects.create_user(
            email="grace@example.com", password="pw", first_name="Grace", last_name="Nduta"
        )
        self.amina = User.objects.create_user(
            email="amina@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )
        self.authenticate(self.grace)

        self.grace_standup = create_standup(
            user=self.grace,
            validated_data={
                "standup_date": datetime.date(2026, 7, 13),
                "blockers": "Waiting on MTN API access.",
                "items": [
                    {
                        "section": "COMPLETED",
                        "content": "Shipped the login endpoint.",
                        "position": 1,
                    },
                    {
                        "section": "CURRENT",
                        "content": "Working on the standups API.",
                        "position": 1,
                    },
                    {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 1},
                    {
                        "section": "MEETING",
                        "content": "Sync with the MTN integration team.",
                        "position": 1,
                    },
                ],
            },
        )
        self.amina_standup = create_standup(
            user=self.amina,
            validated_data={
                "standup_date": datetime.date(2026, 7, 20),
                "blockers": "",
                "items": [
                    {"section": "COMPLETED", "content": "Reviewed pull requests.", "position": 1},
                    {"section": "CURRENT", "content": "Investigating a bug.", "position": 1},
                    {"section": "PLANNED", "content": "Write more tests.", "position": 1},
                ],
            },
        )

    def _ids(self, response):
        return [row["id"] for row in self.get_data(response)["results"]]

    def test_filter_by_user(self):
        response = self.client.get(self.url, {"user": self.grace.id})

        self.assertEqual(self._ids(response), [self.grace_standup.id])

    def test_filter_by_exact_standup_date(self):
        response = self.client.get(self.url, {"standup_date": "2026-07-20"})

        self.assertEqual(self._ids(response), [self.amina_standup.id])

    def test_filter_by_date_range(self):
        response = self.client.get(
            self.url, {"date_after": "2026-07-15", "date_before": "2026-07-31"}
        )

        self.assertEqual(self._ids(response), [self.amina_standup.id])

    def test_filter_by_section(self):
        response = self.client.get(self.url, {"section": "MEETING"})

        self.assertEqual(self._ids(response), [self.grace_standup.id])

    def test_search_by_first_name(self):
        response = self.client.get(self.url, {"search": "Amina"})

        self.assertEqual(self._ids(response), [self.amina_standup.id])

    def test_search_by_last_name(self):
        response = self.client.get(self.url, {"search": "Otieno"})

        self.assertEqual(self._ids(response), [self.amina_standup.id])

    def test_search_by_standup_item_content(self):
        response = self.client.get(self.url, {"search": "pull requests"})

        self.assertEqual(self._ids(response), [self.amina_standup.id])

    def test_search_by_blockers(self):
        response = self.client.get(self.url, {"search": "MTN"})

        self.assertEqual(self._ids(response), [self.grace_standup.id])

    def test_duplicate_results_are_not_returned(self):
        # "MTN" matches both blockers AND a MEETING item's content on
        # Grace's standup (which has 4 items) — without distinct() the
        # items join would multiply that single standup into several rows.
        response = self.client.get(self.url, {"search": "MTN"})

        self.assertEqual(self._ids(response), [self.grace_standup.id])
        self.assertEqual(self.get_data(response)["count"], 1)

    def test_filters_can_be_combined(self):
        response = self.client.get(self.url, {"user": self.grace.id, "section": "MEETING"})

        self.assertEqual(self._ids(response), [self.grace_standup.id])

    def test_combined_filters_returning_nothing(self):
        response = self.client.get(self.url, {"user": self.amina.id, "section": "MEETING"})

        self.assertEqual(self._ids(response), [])

    def test_pagination_still_works(self):
        response = self.client.get(self.url, {"page_size": 1})

        data = self.get_data(response)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["count"], 2)
        self.assertIsNotNone(data["next"])

    def test_invalid_user_filter_uses_standard_error_format(self):
        response = self.client.get(self.url, {"user": "not-a-number"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_error(response)["code"], "VALIDATION_ERROR")

    def test_invalid_section_filter_uses_standard_error_format(self):
        response = self.client.get(self.url, {"section": "NOT_A_SECTION"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_error(response)["code"], "VALIDATION_ERROR")

    def test_invalid_date_filter_uses_standard_error_format(self):
        response = self.client.get(self.url, {"standup_date": "not-a-date"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get_error(response)["code"], "VALIDATION_ERROR")

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
