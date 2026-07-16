import datetime

from django.http import Http404
from django.test import TestCase

from apps.accounts.models import User
from apps.aob.selectors import get_aob_item_by_id, list_aob_items
from apps.aob.services import create_aob_item

MONDAY = datetime.date(2026, 7, 13)


def _valid_data(**overrides):
    data = {
        "title": "Office move",
        "description": "",
        "external_url": "",
        "week_start": MONDAY,
        "position": 1,
    }
    data.update(overrides)
    return data


class GetAOBItemByIdSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.item = create_aob_item(
            created_by=self.user,
            validated_data={
                "title": "Office move",
                "description": "",
                "external_url": "",
                "week_start": MONDAY,
                "position": 1,
            },
        )

    def test_selector_returns_the_correct_item(self):
        result = get_aob_item_by_id(self.item.id)

        self.assertEqual(result.id, self.item.id)
        self.assertEqual(result.title, "Office move")

    def test_raises_404_for_nonexistent_item(self):
        with self.assertRaises(Http404):
            get_aob_item_by_id(999999)


class ListAOBItemsSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.other = User.objects.create_user(email="other@example.com", password="pw")

    def test_returns_items_from_all_users(self):
        create_aob_item(created_by=self.user, validated_data=_valid_data(title="A"))
        create_aob_item(created_by=self.other, validated_data=_valid_data(title="B"))

        self.assertEqual(len(list(list_aob_items())), 2)

    def test_ordered_by_week_start_desc_position_asc_created_at_desc(self):
        older_week = create_aob_item(
            created_by=self.user, validated_data=_valid_data(title="Old", week_start=MONDAY)
        )
        newer_week_pos_2 = create_aob_item(
            created_by=self.user,
            validated_data=_valid_data(
                title="New2", week_start=MONDAY + datetime.timedelta(days=7), position=2
            ),
        )
        newer_week_pos_1 = create_aob_item(
            created_by=self.user,
            validated_data=_valid_data(
                title="New1", week_start=MONDAY + datetime.timedelta(days=7), position=1
            ),
        )

        ids = [item.id for item in list_aob_items()]

        self.assertEqual(ids, [newer_week_pos_1.id, newer_week_pos_2.id, older_week.id])

    def test_empty_database_returns_empty_queryset(self):
        self.assertEqual(list(list_aob_items()), [])

    def test_avoids_unnecessary_database_queries(self):
        for i in range(3):
            create_aob_item(created_by=self.user, validated_data=_valid_data(title=f"Item {i}"))

        with self.assertNumQueries(1):
            items = list(list_aob_items())
            for item in items:
                _ = item.created_by.email
