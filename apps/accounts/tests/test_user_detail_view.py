from apps.accounts.models import User
from tests.base import BaseAPITestCase

EXPECTED_FIELDS = {
    "id",
    "email",
    "first_name",
    "last_name",
    "display_name",
    "is_active",
    "date_joined",
}


class UserDetailViewTests(BaseAPITestCase):
    def setUp(self):
        self.requester = User.objects.create_user(email="requester@example.com", password="pw")
        self.grace = User.objects.create_user(
            email="grace@example.com", password="pw", first_name="Grace", last_name="Nduta"
        )
        self.inactive = User.objects.create_user(
            email="inactive@example.com",
            password="pw",
            first_name="Zed",
            last_name="Inactive",
            is_active=False,
        )
        self.authenticate(self.requester)

    def _url(self, user_id):
        return f"/api/v1/users/{user_id}/"

    def test_authenticated_user_can_retrieve_an_active_user(self):
        response = self.client.get(self._url(self.grace.id))

        self.assertEqual(response.status_code, 200)

    def test_returns_the_correct_user(self):
        response = self.client.get(self._url(self.grace.id))

        data = self.get_data(response)
        self.assertEqual(data["id"], self.grace.id)
        self.assertEqual(data["email"], "grace@example.com")
        self.assertEqual(data["display_name"], "Grace Nduta")

    def test_returns_expected_fields_only(self):
        response = self.client.get(self._url(self.grace.id))

        data = self.get_data(response)
        self.assertEqual(set(data.keys()), EXPECTED_FIELDS)
        self.assertNotIn("password", data)
        self.assertNotIn("is_staff", data)
        self.assertNotIn("is_superuser", data)
        self.assertNotIn("groups", data)
        self.assertNotIn("user_permissions", data)

    def test_inactive_user_is_not_accessible(self):
        response = self.client.get(self._url(self.inactive.id))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")

    def test_nonexistent_user_returns_404_with_standard_error_format(self):
        response = self.client.get(self._url(999999))

        self.assertEqual(response.status_code, 404)
        error = self.get_error(response)
        self.assertEqual(error["code"], "NOT_FOUND")
        self.assertIn("message", error)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self._url(self.grace.id))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
