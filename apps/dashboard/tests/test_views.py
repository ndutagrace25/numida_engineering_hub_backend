import datetime

from django.utils import timezone

from apps.accounts.models import User
from apps.aob.services import create_aob_item
from apps.presence.models import UserPresence
from apps.pto.services import create_pto_entry
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.services import create_pull_request_link
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
        self.amina = User.objects.create_user(
            email="amina@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )
        self.authenticate(self.grace)

    def _create_standup(self, user, standup_date):
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
        self._create_standup(self.grace, WEEK_START)

        response = self._get(WEEK_START.isoformat())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Dashboard retrieved successfully.")
        data = self.get_data(response)
        self.assertEqual(data["week_start"], "2026-07-13")
        self.assertEqual(data["week_end"], "2026-07-19")

        summary = data["standup_summary"]
        self.assertEqual(summary["total_active_users"], 2)
        self.assertEqual(summary["total_submitted_standups"], 1)
        self.assertEqual([u["first_name"] for u in summary["users_who_submitted"]], ["Grace"])
        self.assertEqual(
            [u["first_name"] for u in summary["users_who_have_not_submitted"]], ["Amina"]
        )
        self.assertEqual(len(data["weekly_standups"]), 1)

    def test_standup_summary_uses_limited_non_sensitive_user_details(self):
        self._create_standup(self.grace, WEEK_START)

        response = self._get(WEEK_START.isoformat())

        data = self.get_data(response)
        for user in data["standup_summary"]["users_who_submitted"]:
            self.assertNotIn("email", user)
            self.assertNotIn("is_active", user)
        for user in data["standup_summary"]["users_who_have_not_submitted"]:
            self.assertNotIn("email", user)
            self.assertNotIn("is_active", user)

    def test_aob_items_within_week_are_included(self):
        create_aob_item(
            user=self.grace,
            validated_data={
                "title": "Office closed Friday",
                "description": "",
                "external_url": "",
                "week_start": WEEK_START,
                "position": 1,
            },
        )

        response = self._get(WEEK_START.isoformat())

        data = self.get_data(response)
        self.assertEqual(len(data["aob_items"]), 1)
        self.assertEqual(data["aob_items"][0]["title"], "Office closed Friday")

    def test_pull_request_links_within_week_are_included(self):
        create_pull_request_link(
            created_by=self.grace,
            validated_data={
                "title": "Fix bug",
                "url": "https://github.com/org/repo/pull/1",
                "group_name": "App PRs",
                "status": PullRequestLink.Status.OPEN,
                "week_start": WEEK_START,
                "position": 1,
            },
        )

        response = self._get(WEEK_START.isoformat())

        data = self.get_data(response)
        self.assertEqual(len(data["pull_request_links"]), 1)
        self.assertEqual(data["pull_request_links"][0]["title"], "Fix bug")

    def test_pto_entries_overlapping_week_are_included(self):
        create_pto_entry(
            created_by=self.grace,
            validated_data={
                "user": self.grace,
                "start_date": WEEK_START - datetime.timedelta(days=2),
                "end_date": WEEK_START + datetime.timedelta(days=1),
                "reason": "",
                "handover_url": "",
            },
        )
        create_pto_entry(
            created_by=self.grace,
            validated_data={
                "user": self.amina,
                "start_date": WEEK_END + datetime.timedelta(days=5),
                "end_date": WEEK_END + datetime.timedelta(days=7),
                "reason": "",
                "handover_url": "",
            },
        )

        response = self._get(WEEK_START.isoformat())

        data = self.get_data(response)
        self.assertEqual(len(data["pto_entries"]), 1)
        self.assertEqual(data["pto_entries"][0]["user"]["id"], self.grace.id)

    def test_presence_reflects_current_state(self):
        UserPresence.objects.create(user=self.grace, last_seen_at=timezone.now())

        response = self._get(WEEK_START.isoformat())

        data = self.get_data(response)
        online_ids = [entry["user"]["id"] for entry in data["presence"]["online"]]
        self.assertIn(self.grace.id, online_ids)

    def test_week_with_no_data_returns_valid_empty_data(self):
        response = self._get(WEEK_START.isoformat())

        data = self.get_data(response)
        self.assertEqual(data["standup_summary"]["total_submitted_standups"], 0)
        self.assertEqual(data["standup_summary"]["users_who_submitted"], [])
        self.assertEqual(data["weekly_standups"], [])
        self.assertEqual(data["aob_items"], [])
        self.assertEqual(data["pto_entries"], [])
        self.assertEqual(data["pull_request_links"], [])
        self.assertEqual(data["presence"]["online"], [])

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

    def test_query_count_does_not_grow_with_more_data(self):
        self._create_standup(self.grace, WEEK_START)
        create_aob_item(
            user=self.grace,
            validated_data={
                "title": "Item",
                "description": "",
                "external_url": "",
                "week_start": WEEK_START,
                "position": 1,
            },
        )
        create_pull_request_link(
            created_by=self.grace,
            validated_data={
                "title": "PR",
                "url": "https://github.com/org/repo/pull/1",
                "group_name": "App PRs",
                "status": PullRequestLink.Status.OPEN,
                "week_start": WEEK_START,
                "position": 1,
            },
        )
        create_pto_entry(
            created_by=self.grace,
            validated_data={
                "user": self.grace,
                "start_date": WEEK_START,
                "end_date": WEEK_START,
                "reason": "",
                "handover_url": "",
            },
        )
        UserPresence.objects.create(user=self.grace, last_seen_at=timezone.now())

        with self.assertNumQueries(10):
            self._get(WEEK_START.isoformat())

        extra_users = [
            User.objects.create_user(email=f"extra{i}@example.com", password="pw") for i in range(5)
        ]
        for offset, user in enumerate(extra_users):
            self._create_standup(user, WEEK_START + datetime.timedelta(days=offset % 7))
            create_aob_item(
                user=user,
                validated_data={
                    "title": f"Item {offset}",
                    "description": "",
                    "external_url": "",
                    "week_start": WEEK_START,
                    "position": offset + 2,
                },
            )

        with self.assertNumQueries(10):
            self._get(WEEK_START.isoformat())
