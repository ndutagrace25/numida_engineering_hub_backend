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


class UserListViewTests(BaseAPITestCase):
    url = "/api/v1/users/"

    def setUp(self):
        self.requester = User.objects.create_user(email="requester@example.com", password="pw")
        self.grace = User.objects.create_user(
            email="grace@example.com", password="pw", first_name="Grace", last_name="Nduta"
        )
        self.amina = User.objects.create_user(
            email="amina@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )
        self.inactive = User.objects.create_user(
            email="inactive@example.com",
            password="pw",
            first_name="Zed",
            last_name="Inactive",
            is_active=False,
        )
        self.authenticate(self.requester)

    def test_authenticated_user_can_retrieve_list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_only_active_users_are_returned(self):
        response = self.client.get(self.url)

        emails = {row["email"] for row in self.get_data(response)["results"]}
        self.assertIn("grace@example.com", emails)
        self.assertNotIn("inactive@example.com", emails)

    def test_users_are_ordered_by_first_then_last_name(self):
        response = self.client.get(self.url)

        first_names = [row["first_name"] for row in self.get_data(response)["results"]]
        self.assertEqual(first_names, sorted(first_names))

    def test_search_by_first_name(self):
        response = self.client.get(self.url, {"search": "Grace"})

        results = self.get_data(response)["results"]
        self.assertEqual({row["email"] for row in results}, {"grace@example.com"})

    def test_search_by_last_name(self):
        response = self.client.get(self.url, {"search": "Otieno"})

        results = self.get_data(response)["results"]
        self.assertEqual({row["email"] for row in results}, {"amina@example.com"})

    def test_search_by_email(self):
        response = self.client.get(self.url, {"search": "amina@example.com"})

        results = self.get_data(response)["results"]
        self.assertEqual({row["email"] for row in results}, {"amina@example.com"})

    def test_pagination_works(self):
        response = self.client.get(self.url, {"page_size": 1})

        data = self.get_data(response)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["count"], 3)  # requester + grace + amina (inactive excluded)
        self.assertIsNotNone(data["next"])

    def test_password_and_sensitive_fields_are_not_included(self):
        response = self.client.get(self.url)

        for row in self.get_data(response)["results"]:
            self.assertEqual(set(row.keys()), EXPECTED_FIELDS)
            self.assertNotIn("password", row)
            self.assertNotIn("is_staff", row)
            self.assertNotIn("is_superuser", row)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")
