import datetime

from apps.accounts.models import User
from apps.standups.models import StandupItem
from apps.standups.services import create_standup
from tests.base import BaseAPITestCase


def _valid_items():
    return [
        {"section": "COMPLETED", "content": "Shipped the login endpoint.", "position": 1},
        {"section": "CURRENT", "content": "Working on the standups API.", "position": 1},
        {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 1},
    ]


class StandupUpdateViewTests(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.standup = create_standup(
            user=self.user,
            validated_data={
                "standup_date": datetime.date(2026, 7, 13),
                "blockers": "Original blocker.",
                "items": _valid_items(),
            },
        )
        self.authenticate(self.user)

    def _url(self, standup_id=None):
        return f"/api/v1/standups/{standup_id or self.standup.id}/"

    def test_owner_can_update_their_standup(self):
        response = self.client.patch(self._url(), {"blockers": "Updated blocker."}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Standup updated successfully.")

    def test_standup_fields_are_updated_correctly(self):
        response = self.client.patch(
            self._url(),
            {"standup_date": "2026-07-20", "blockers": "Updated blocker."},
            format="json",
        )

        data = self.get_data(response)
        self.assertEqual(data["standup_date"], "2026-07-20")
        self.assertEqual(data["blockers"], "Updated blocker.")

    def test_nested_items_are_replaced_correctly(self):
        new_items = [
            {"section": "COMPLETED", "content": "New completed.", "position": 1},
            {"section": "CURRENT", "content": "New current.", "position": 1},
            {"section": "PLANNED", "content": "New planned.", "position": 1},
        ]

        response = self.client.patch(self._url(), {"items": new_items}, format="json")

        data = self.get_data(response)
        contents = {item["content"] for item in data["items"]}
        self.assertEqual(contents, {"New completed.", "New current.", "New planned."})

    def test_new_items_are_created(self):
        new_items = _valid_items()
        new_items.append({"section": "MEETING", "content": "Standup sync.", "position": 1})

        response = self.client.patch(self._url(), {"items": new_items}, format="json")

        data = self.get_data(response)
        self.assertEqual(len(data["items"]), 4)
        self.assertTrue(any(item["section"] == "MEETING" for item in data["items"]))

    def test_removed_items_are_deleted(self):
        old_item_ids = set(self.standup.items.values_list("id", flat=True))

        self.client.patch(self._url(), {"items": _valid_items()}, format="json")

        self.assertFalse(StandupItem.objects.filter(id__in=old_item_ids).exists())

    def test_item_positions_are_preserved(self):
        new_items = _valid_items()
        new_items[2]["position"] = 9

        response = self.client.patch(self._url(), {"items": new_items}, format="json")

        data = self.get_data(response)
        planned = next(item for item in data["items"] if item["section"] == "PLANNED")
        self.assertEqual(planned["position"], 9)

    def test_owner_cannot_be_changed(self):
        other = User.objects.create_user(email="other@example.com", password="pw")

        response = self.client.patch(
            self._url(), {"user": other.id, "blockers": "Updated."}, format="json"
        )

        data = self.get_data(response)
        self.assertEqual(data["user"]["email"], "jane@example.com")
        self.standup.refresh_from_db()
        self.assertEqual(self.standup.user, self.user)

    def test_user_cannot_update_another_users_standup(self):
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.authenticate(other)

        response = self.client.patch(self._url(), {"blockers": "Hijacked."}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_error(response)["code"], "PERMISSION_DENIED")

    def test_updating_to_a_duplicate_date_for_same_user_is_rejected(self):
        create_standup(
            user=self.user,
            validated_data={
                "standup_date": datetime.date(2026, 7, 14),
                "blockers": "",
                "items": _valid_items(),
            },
        )

        response = self.client.patch(self._url(), {"standup_date": "2026-07-14"}, format="json")

        self.assertEqual(response.status_code, 400)
        error = self.get_error(response)
        self.assertEqual(error["code"], "VALIDATION_ERROR")
        self.assertIn("standup_date", error["fields"])

    def test_invalid_data_uses_standard_error_format(self):
        response = self.client.patch(
            self._url(),
            {"items": [{"section": "COMPLETED", "content": "Only completed.", "position": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(set(body["error"].keys()), {"code", "message", "fields"})

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.patch(self._url(), {"blockers": "x"}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get_error(response)["code"], "NOT_AUTHENTICATED")

    def test_nonexistent_standup_returns_standard_404(self):
        response = self.client.patch(self._url(999999), {"blockers": "x"}, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.get_error(response)["code"], "NOT_FOUND")
