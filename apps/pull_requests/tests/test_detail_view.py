import datetime

from apps.accounts.models import User
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.services import create_pull_request_link
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


class PullRequestLinkDetailViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.link = create_pull_request_link(
            created_by=self.user,
            validated_data={
                "title": "Fix login bug",
                "url": "https://github.com/org/repo/pull/6905",
                "group_name": "App 3.0 PRs",
                "status": PullRequestLink.Status.OPEN,
                "week_start": MONDAY,
                "position": 1,
            },
        )

    def _url(self, link_id=None):
        return f"/api/v1/pull-request-links/{link_id or self.link.id}/"

    def test_any_authenticated_user_can_view_detail(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Pull request link retrieved successfully.")

    def test_nonexistent_link_returns_standard_404(self):
        self.authenticate(self.user)

        response = self.client.get(self._url(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")

    def test_unauthenticated_requests_are_rejected(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
