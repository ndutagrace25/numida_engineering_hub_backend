import datetime

from apps.accounts.models import User
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


def _valid_payload(**overrides):
    data = {
        "title": "Fix login bug",
        "url": "https://github.com/org/repo/pull/6905",
        "group_name": "App 3.0 PRs",
        "status": "OPEN",
        "week_start": MONDAY.isoformat(),
        "position": 1,
    }
    data.update(overrides)
    return data


class PullRequestLinkCreateViewTests(BaseAPITestCase):
    url = "/api/v1/pull-request-links/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.authenticate(self.user)

    def test_valid_pr_link_can_be_created(self):
        response = self.client.post(self.url, _valid_payload(), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "Pull request link created successfully.")

    def test_authenticated_user_is_assigned_as_created_by(self):
        response = self.client.post(self.url, _valid_payload(), format="json")

        data = self.get_data(response)
        self.assertEqual(data["created_by"]["id"], self.user.id)

    def test_http_urls_are_rejected(self):
        response = self.client.post(
            self.url, _valid_payload(url="http://github.com/org/repo/pull/6905"), format="json"
        )

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("url", error["fields"])

    def test_https_urls_are_accepted(self):
        response = self.client.post(
            self.url, _valid_payload(url="https://github.com/org/repo/pull/6905"), format="json"
        )

        self.assertEqual(response.status_code, 201)

    def test_non_monday_week_start_is_rejected(self):
        response = self.client.post(
            self.url, _valid_payload(week_start="2026-07-14"), format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("week_start", self.get_error(response)["fields"])

    def test_invalid_status_values_are_rejected(self):
        response = self.client.post(self.url, _valid_payload(status="NOT_A_STATUS"), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("status", self.get_error(response)["fields"])

    def test_negative_position_values_are_rejected(self):
        response = self.client.post(self.url, _valid_payload(position=-1), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("position", self.get_error(response)["fields"])

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, _valid_payload(), format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_sensitive_creator_fields_are_not_exposed(self):
        response = self.client.post(self.url, _valid_payload(), format="json")

        creator = self.get_data(response)["created_by"]
        self.assertNotIn("email", creator)
        self.assertNotIn("password", creator)
        self.assertNotIn("is_active", creator)
