from django.contrib.auth import SESSION_KEY
from django.utils import timezone

from apps.accounts.models import User
from apps.presence.models import UserPresence
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


class LogoutViewTests(BaseAPITestCase):
    login_url = "/api/v1/auth/login/"
    logout_url = "/api/v1/auth/logout/"

    def setUp(self):
        self.password = "s3cret-pw"
        self.user = User.objects.create_user(email="jane@example.com", password=self.password)

    def _login(self):
        return self.client.post(
            self.login_url, {"email": self.user.email, "password": self.password}
        )

    def test_authenticated_user_can_log_out(self):
        self._login()

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 200)

    def test_logout_returns_standard_success_response_with_null_data(self):
        self._login()

        response = self.client.post(self.logout_url)

        body = response.json()
        self.assertEqual(body["message"], "Logout successful.")
        self.assertIsNone(body["data"])

    def test_logout_exposes_no_user_or_session_data(self):
        self._login()

        response = self.client.post(self.logout_url)

        self.assertEqual(set(response.json().keys()), {"message", "data"})

    def test_session_is_cleared_after_logout(self):
        self._login()
        self.assertIn(SESSION_KEY, self.client.session)

        self.client.post(self.logout_url)

        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_old_session_cannot_access_authenticated_endpoints_after_logout(self):
        self._login()
        self.client.post(self.logout_url)

        # Same client, now logged out: a second call to an authenticated
        # endpoint (logout itself) must be rejected, not silently succeed.
        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_logout_returns_standard_auth_error(self):
        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 401)
        error = self.get_error(response)
        self.assertEqual(error["code"], "NOT_AUTHENTICATED")

    def test_logout_clears_the_user_s_presence_record(self):
        self._login()
        UserPresence.objects.create(user=self.user, last_seen_at=timezone.now())

        self.client.post(self.logout_url)

        self.assertFalse(UserPresence.objects.filter(user=self.user).exists())

    def test_logout_does_not_error_when_user_has_no_presence_record(self):
        self._login()
        self.assertFalse(UserPresence.objects.filter(user=self.user).exists())

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 200)


class CurrentUserViewTests(BaseAPITestCase):
    url = "/api/v1/auth/me/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com",
            password="s3cret-pw",
            first_name="Jane",
            last_name="Doe",
        )

    def test_authenticated_user_receives_200(self):
        self.authenticate(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_returns_the_logged_in_user(self):
        self.authenticate(self.user)

        response = self.client.get(self.url)

        data = self.get_data(response)
        self.assertEqual(data["id"], self.user.id)
        self.assertEqual(data["email"], "jane@example.com")

    def test_returns_expected_fields(self):
        self.authenticate(self.user)

        response = self.client.get(self.url)

        data = self.get_data(response)
        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "email",
                "first_name",
                "last_name",
                "display_name",
                "is_active",
                "date_joined",
            },
        )
        self.assertEqual(data["display_name"], "Jane Doe")

    def test_password_and_sensitive_fields_are_not_included(self):
        self.authenticate(self.user)

        response = self.client.get(self.url)

        data = self.get_data(response)
        self.assertNotIn("password", data)
        self.assertNotIn("sessionid", data)
        self.assertNotIn("permissions", data)
        self.assertNotIn("is_staff", data)
        self.assertNotIn("is_superuser", data)

    def test_unauthenticated_request_returns_standard_auth_error(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        error = self.get_error(response)
        self.assertEqual(error["code"], "NOT_AUTHENTICATED")
