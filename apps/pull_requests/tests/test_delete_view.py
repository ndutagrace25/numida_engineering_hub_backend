import datetime

from apps.accounts.models import User
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.services import create_pull_request_link
from tests.base import BaseAPITestCase

MONDAY = datetime.date(2026, 7, 13)


class PullRequestLinkDeleteViewTests(BaseAPITestCase):
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
        self.authenticate(self.user)

    def _url(self, link_id=None):
        return f"/api/v1/pull-request-links/{link_id or self.link.id}/"

    def test_creator_can_delete_the_link(self):
        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"message": "Pull request link deleted successfully.", "data": None},
        )
        self.assertFalse(PullRequestLink.objects.filter(id=self.link.id).exists())

    def test_another_user_cannot_delete_the_link(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_error(response)["code"], "PERMISSION_DENIED")
        self.assertTrue(PullRequestLink.objects.filter(id=self.link.id).exists())

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.delete(self._url())

        self.assertEqual(response.status_code, 401)
        self.assertTrue(PullRequestLink.objects.filter(id=self.link.id).exists())

    def test_nonexistent_link_returns_standard_404(self):
        response = self.client.delete(self._url(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")
