from django.contrib.auth import SESSION_KEY

from apps.accounts.models import User
from tests.base import BaseAPITestCase


class LoginViewTests(BaseAPITestCase):
    url = "/api/v1/auth/login/"

    def setUp(self):
        self.password = "s3cret-pw"
        self.user = User.objects.create_user(
            email="jane@example.com",
            password=self.password,
            first_name="Jane",
            last_name="Doe",
        )

    def _login(self, email, password):
        return self.client.post(self.url, {"email": email, "password": password})

    def test_valid_credentials_return_200(self):
        response = self._login(self.user.email, self.password)

        self.assertEqual(response.status_code, 200)

    def test_valid_credentials_create_session(self):
        self._login(self.user.email, self.password)

        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_valid_credentials_return_current_user_data_without_password(self):
        response = self._login(self.user.email, self.password)

        data = self.get_data(response)
        self.assertEqual(data["email"], self.user.email)
        self.assertEqual(data["first_name"], "Jane")
        self.assertEqual(data["last_name"], "Doe")
        self.assertEqual(data["display_name"], "Jane Doe")
        self.assertNotIn("password", data)

    def test_invalid_password_is_rejected(self):
        response = self._login(self.user.email, "wrong-password")

        self.assertIn(response.status_code, (400, 401))
        error = self.get_error(response)
        self.assertIn("code", error)
        self.assertIn("message", error)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_unknown_email_is_rejected(self):
        response = self._login("nobody@example.com", "whatever")

        self.assertIn(response.status_code, (400, 401))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self._login(self.user.email, self.password)

        self.assertIn(response.status_code, (400, 401))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_already_authenticated_user_can_log_in_again_safely(self):
        self._login(self.user.email, self.password)
        first_session_key = self.client.session.session_key

        response = self._login(self.user.email, self.password)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)
        # Re-logging in as the *same* user shouldn't force a brand new
        # session; Django's login() only flushes when the user differs.
        self.assertEqual(self.client.session.session_key, first_session_key)

    def test_logging_in_as_different_user_replaces_session(self):
        other = User.objects.create_user(email="other@example.com", password="other-pw")

        self._login(self.user.email, self.password)
        response = self._login(other.email, "other-pw")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session[SESSION_KEY]), other.pk)
