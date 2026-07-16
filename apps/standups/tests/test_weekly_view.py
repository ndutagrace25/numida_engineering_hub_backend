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


class WeeklyStandupsViewTests(BaseAPITestCase):
    url = "/api/v1/standups/weekly/"
    # A known Monday.
    WEEK_START = datetime.date(2026, 7, 13)
    WEEK_END = datetime.date(2026, 7, 19)

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

    def _get(self, week_start=None):
        params = {} if week_start is None else {"week_start": week_start}
        return self.client.get(self.url, params)

    def test_returns_all_standups_within_the_selected_week(self):
        self._create(self.user, self.WEEK_START)
        self._create(self.other, self.WEEK_END)

        response = self._get(self.WEEK_START.isoformat())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.get_data(response)), 2)

    def test_excludes_standups_before_and_after_the_selected_week(self):
        self._create(self.user, self.WEEK_START - datetime.timedelta(days=1))
        self._create(self.other, self.WEEK_END + datetime.timedelta(days=1))

        response = self._get(self.WEEK_START.isoformat())

        self.assertEqual(self.get_data(response), [])

    def test_includes_standups_from_different_users(self):
        self._create(self.user, self.WEEK_START)
        self._create(self.other, self.WEEK_START + datetime.timedelta(days=1))

        response = self._get(self.WEEK_START.isoformat())

        emails = {row["user"]["email"] for row in self.get_data(response)}
        self.assertEqual(emails, {"jane@example.com", "other@example.com"})

    def test_includes_nested_standup_items(self):
        self._create(self.user, self.WEEK_START)

        response = self._get(self.WEEK_START.isoformat())

        self.assertEqual(len(self.get_data(response)[0]["items"]), 3)

    def test_results_are_ordered_correctly(self):
        later = self._create(self.user, self.WEEK_START + datetime.timedelta(days=2))
        earlier = self._create(self.other, self.WEEK_START)

        response = self._get(self.WEEK_START.isoformat())

        ids = [row["id"] for row in self.get_data(response)]
        self.assertEqual(ids, [earlier.id, later.id])

    def test_missing_week_start_is_rejected(self):
        response = self._get()

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("week_start", error["fields"])

    def test_invalid_date_is_rejected(self):
        response = self._get("not-a-date")

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("week_start", error["fields"])

    def test_non_monday_week_start_is_rejected(self):
        # 2026-07-14 is a Tuesday.
        response = self._get("2026-07-14")

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("week_start", error["fields"])

    def test_week_with_no_standups_returns_empty_list(self):
        response = self._get(self.WEEK_START.isoformat())

        self.assertEqual(self.get_data(response), [])

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self._get(self.WEEK_START.isoformat())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_sensitive_user_fields_are_not_exposed(self):
        self._create(self.user, self.WEEK_START)

        response = self._get(self.WEEK_START.isoformat())

        user_data = self.get_data(response)[0]["user"]
        self.assertNotIn("password", user_data)
        self.assertNotIn("is_staff", user_data)
        self.assertNotIn("is_superuser", user_data)
