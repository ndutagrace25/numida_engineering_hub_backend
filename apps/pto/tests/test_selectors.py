import datetime

from django.http import Http404
from django.test import TestCase

from apps.accounts.models import User
from apps.pto.selectors import get_pto_entry_by_id, list_pto_entries
from apps.pto.services import create_pto_entry


class GetPTOEntryByIdSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")
        self.entry = create_pto_entry(
            created_by=self.creator,
            validated_data={
                "user": self.user,
                "start_date": datetime.date(2026, 7, 13),
                "end_date": datetime.date(2026, 7, 17),
            },
        )

    def test_returns_the_correct_entry(self):
        result = get_pto_entry_by_id(self.entry.id)

        self.assertEqual(result.id, self.entry.id)

    def test_raises_404_for_nonexistent_entry(self):
        with self.assertRaises(Http404):
            get_pto_entry_by_id(999999)


class ListPTOEntriesSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.creator = User.objects.create_user(email="creator@example.com", password="pw")

    def _create(self, **overrides):
        data = {
            "user": self.user,
            "start_date": datetime.date(2026, 7, 13),
            "end_date": datetime.date(2026, 7, 17),
        }
        data.update(overrides)
        return create_pto_entry(created_by=self.creator, validated_data=data)

    def test_returns_all_entries(self):
        self._create()
        self._create(start_date=datetime.date(2026, 8, 1), end_date=datetime.date(2026, 8, 3))

        self.assertEqual(len(list(list_pto_entries())), 2)

    def test_ordered_by_start_date_then_end_date_then_user_name(self):
        later = self._create(
            start_date=datetime.date(2026, 8, 1), end_date=datetime.date(2026, 8, 3)
        )
        earlier = self._create(
            start_date=datetime.date(2026, 7, 1), end_date=datetime.date(2026, 7, 3)
        )

        ids = [entry.id for entry in list_pto_entries()]

        self.assertEqual(ids, [earlier.id, later.id])

    def test_empty_database_returns_empty_queryset(self):
        self.assertEqual(list(list_pto_entries()), [])

    def test_avoids_unnecessary_database_queries(self):
        for offset in range(3):
            self._create(
                start_date=datetime.date(2026, 7, 13) + datetime.timedelta(days=offset * 10),
                end_date=datetime.date(2026, 7, 15) + datetime.timedelta(days=offset * 10),
            )

        with self.assertNumQueries(1):
            entries = list(list_pto_entries())
            for entry in entries:
                _ = entry.user.email
                _ = entry.created_by.email
