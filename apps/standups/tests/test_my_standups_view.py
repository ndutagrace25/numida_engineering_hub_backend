import datetime

from apps.accounts.models import User
from apps.standups.services import create_standup
from tests.base import BaseAPITestCase


def _valid_items():
    return [
        {"section": "COMPLETED", "content": "Shipped the login endpoint.", "position": 1},
        {"section": "CURRENT", "content": "Working on the standups API.", "position": 1},
        {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 1},
    ]


class MyStandupsListViewTests(BaseAPITestCase):
    url = "/api/v1/standups/mine/"

    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(self.user)

    def _create(self, user, standup_date):
        return create_standup(
            user=user,
            validated_data={
                "standup_date": standup_date,
                "blockers": "",
                "items": _valid_items(),
            },
        )

    def test_authenticated_users_receive_only_their_own_standups(self):
        self._create(self.user, datetime.date(2026, 7, 13))
        self._create(self.other, datetime.date(2026, 7, 14))

        response = self.client.get(self.url)

        emails = {row["user"]["email"] for row in self.get_data(response)["results"]}
        self.assertEqual(emails, {"jane@example.com"})

    def test_standups_belonging_to_other_users_are_excluded(self):
        self._create(self.other, datetime.date(2026, 7, 13))

        response = self.client.get(self.url)

        self.assertEqual(self.get_data(response)["results"], [])

    def test_results_are_ordered_correctly(self):
        older = self._create(self.user, datetime.date(2026, 7, 10))
        newer = self._create(self.user, datetime.date(2026, 7, 15))

        response = self.client.get(self.url)

        ids = [row["id"] for row in self.get_data(response)["results"]]
        self.assertEqual(ids, [newer.id, older.id])

    def test_nested_items_are_included(self):
        self._create(self.user, datetime.date(2026, 7, 13))

        response = self.client.get(self.url)

        results = self.get_data(response)["results"]
        self.assertEqual(len(results[0]["items"]), 3)

    def test_pagination_works(self):
        for offset in range(3):
            self._create(self.user, datetime.date(2026, 7, 1) + datetime.timedelta(days=offset))

        response = self.client.get(self.url, {"page_size": 2})

        data = self.get_data(response)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["count"], 3)
        self.assertIsNotNone(data["next"])

    def test_empty_result_returns_empty_paginated_response(self):
        response = self.client.get(self.url)

        data = self.get_data(response)
        self.assertEqual(data["results"], [])
        self.assertEqual(data["count"], 0)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_sensitive_user_fields_are_not_exposed(self):
        self._create(self.user, datetime.date(2026, 7, 13))

        response = self.client.get(self.url)

        user_data = self.get_data(response)["results"][0]["user"]
        self.assertNotIn("password", user_data)
        self.assertNotIn("is_staff", user_data)
        self.assertNotIn("is_superuser", user_data)
