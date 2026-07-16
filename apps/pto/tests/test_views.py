from apps.accounts.models import User
from tests.base import BaseAPITestCase


def _valid_payload(user_id, **overrides):
    data = {
        "user": user_id,
        "start_date": "2026-07-13",
        "end_date": "2026-07-17",
        "reason": "Family vacation.",
        "handover_url": "https://example.com/handover",
    }
    data.update(overrides)
    return data


class PTOEntryCreateViewTests(BaseAPITestCase):
    url = "/api/v1/pto/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")
        self.authenticate(self.creator)

    def test_valid_pto_can_be_created(self):
        response = self.client.post(self.url, _valid_payload(self.user.id), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "PTO entry created successfully.")

    def test_authenticated_user_is_assigned_as_created_by(self):
        response = self.client.post(self.url, _valid_payload(self.user.id), format="json")

        data = self.get_data(response)
        self.assertEqual(data["created_by"]["id"], self.creator.id)

    def test_pto_can_be_created_for_another_active_user(self):
        response = self.client.post(self.url, _valid_payload(self.user.id), format="json")

        data = self.get_data(response)
        self.assertEqual(data["user"]["id"], self.user.id)

    def test_one_day_pto_is_accepted(self):
        response = self.client.post(
            self.url,
            _valid_payload(self.user.id, start_date="2026-07-13", end_date="2026-07-13"),
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_end_date_before_start_date_is_rejected(self):
        response = self.client.post(
            self.url,
            _valid_payload(self.user.id, start_date="2026-07-17", end_date="2026-07-13"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("end_date", error["fields"])

    def test_reason_and_handover_url_are_optional(self):
        payload = _valid_payload(self.user.id)
        del payload["reason"]
        del payload["handover_url"]

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201)

    def test_http_handover_urls_are_rejected(self):
        response = self.client.post(
            self.url,
            _valid_payload(self.user.id, handover_url="http://example.com/handover"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("handover_url", self.get_error(response)["fields"])

    def test_https_handover_urls_are_accepted(self):
        response = self.client.post(
            self.url,
            _valid_payload(self.user.id, handover_url="https://example.com/handover"),
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, _valid_payload(self.user.id), format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_sensitive_user_fields_are_not_exposed(self):
        response = self.client.post(self.url, _valid_payload(self.user.id), format="json")

        data = self.get_data(response)
        for key in ("user", "created_by"):
            fields = data[key]
            self.assertNotIn("email", fields)
            self.assertNotIn("password", fields)
            self.assertNotIn("is_active", fields)
