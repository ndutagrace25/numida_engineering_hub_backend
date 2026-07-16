import datetime

from apps.accounts.models import User
from apps.standups.services import create_standup
from tests.base import BaseAPITestCase

WEEK_START = datetime.date(2026, 7, 13)
WEEK_END = datetime.date(2026, 7, 19)


def _valid_items():
    return [
        {"section": "COMPLETED", "content": "Shipped X.", "position": 1},
        {"section": "CURRENT", "content": "Working on Y.", "position": 1},
        {"section": "PLANNED", "content": "Plan Z.", "position": 1},
    ]


class DashboardViewTests(BaseAPITestCase):
    url = "/api/v1/dashboard/"

    def setUp(self):
        self.grace = User.objects.create_user(
            email="grace@example.com", password="pw", first_name="Grace", last_name="Nduta"
        )
        self.amina = User.objects.create_user(email="amina@example.com", password="pw")
        self.authenticate(self.grace)

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

    def test_returns_dashboard_for_valid_week(self):
        self._create(self.grace, WEEK_START)

        response = self._get(WEEK_START.isoformat())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Dashboard retrieved successfully.")
        data = self.get_data(response)
        self.assertEqual(data["week_start"], "2026-07-13")
        self.assertEqual(data["week_end"], "2026-07-19")
        self.assertEqual(data["total_active_users"], 2)
        self.assertEqual(data["total_submitted_standups"], 1)
        self.assertEqual([u["email"] for u in data["users_who_submitted"]], ["grace@example.com"])
        self.assertEqual(
            [u["email"] for u in data["users_who_have_not_submitted"]], ["amina@example.com"]
        )
        self.assertEqual(len(data["latest_standups"]), 1)

    def test_week_with_no_standups_returns_valid_empty_data(self):
        response = self._get(WEEK_START.isoformat())

        data = self.get_data(response)
        self.assertEqual(data["total_submitted_standups"], 0)
        self.assertEqual(data["users_who_submitted"], [])
        self.assertEqual(data["latest_standups"], [])

    def test_missing_week_start_is_rejected(self):
        response = self._get()

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("week_start", error["fields"])

    def test_invalid_date_is_rejected(self):
        response = self._get("not-a-date")

        self.assertEqual(response.status_code, 400)
        self.assertIn("week_start", self.get_error(response)["fields"])

    def test_non_monday_week_start_is_rejected(self):
        response = self._get("2026-07-14")  # a Tuesday

        self.assertEqual(response.status_code, 400)
        self.assertIn("week_start", self.get_error(response)["fields"])

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self._get(WEEK_START.isoformat())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
