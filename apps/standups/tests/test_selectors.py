import datetime

from django.http import Http404
from django.test import TestCase

from apps.accounts.models import User
from apps.standups.selectors import get_standup_by_id
from apps.standups.services import create_standup


def _valid_items():
    return [
        {"section": "COMPLETED", "content": "Shipped the login endpoint.", "position": 1},
        {"section": "CURRENT", "content": "Working on the standups API.", "position": 1},
        {"section": "PLANNED", "content": "Plan the PTO feature.", "position": 1},
    ]


class GetStandupByIdSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.standup = create_standup(
            user=self.user,
            validated_data={
                "standup_date": datetime.date(2026, 7, 13),
                "blockers": "",
                "items": _valid_items(),
            },
        )

    def test_returns_the_standup(self):
        standup = get_standup_by_id(self.standup.id)

        self.assertEqual(standup.id, self.standup.id)

    def test_raises_404_for_nonexistent_standup(self):
        with self.assertRaises(Http404):
            get_standup_by_id(999999)

    def test_items_are_ordered_by_section_and_position(self):
        standup = get_standup_by_id(self.standup.id)

        sections = [item.section for item in standup.items.all()]
        self.assertEqual(sections, sorted(sections))

    def test_uses_optimized_related_object_loading(self):
        # 1 query for the Standup+user select_related join, 1 for the
        # prefetch_related items — regardless of how many items exist, and
        # with no further queries triggered by accessing them below.
        with self.assertNumQueries(2):
            standup = get_standup_by_id(self.standup.id)
            _ = standup.user.email
            _ = list(standup.items.all())
