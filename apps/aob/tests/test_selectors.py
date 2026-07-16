import datetime

from django.http import Http404
from django.test import TestCase

from apps.accounts.models import User
from apps.aob.selectors import get_aob_item_by_id
from apps.aob.services import create_aob_item

MONDAY = datetime.date(2026, 7, 13)


class GetAOBItemByIdSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.item = create_aob_item(
            user=self.user,
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
