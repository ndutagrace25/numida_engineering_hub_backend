import datetime

from django.http import Http404
from django.test import TestCase

from apps.accounts.models import User
from apps.standups.models import Standup
from apps.standups.selectors import (
    get_standup_by_id,
    list_standups,
    list_user_standups,
    list_weekly_standups,
)
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


class ListStandupsSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.other = User.objects.create_user(email="other@example.com", password="pw")

    def _create(self, user, standup_date):
        return create_standup(
            user=user,
            validated_data={
                "standup_date": standup_date,
                "blockers": "",
                "items": _valid_items(),
            },
        )

    def test_returns_standups_from_all_users(self):
        self._create(self.user, datetime.date(2026, 7, 10))
        self._create(self.other, datetime.date(2026, 7, 11))

        self.assertEqual(len(list(list_standups())), 2)

    def test_ordered_by_standup_date_desc_then_created_at_desc(self):
        older_date = self._create(self.user, datetime.date(2026, 7, 10))
        same_date_first = self._create(self.other, datetime.date(2026, 7, 15))
        same_date_second = self._create(self.user, datetime.date(2026, 7, 15))

        # Force deterministic created_at values for the tie-break, since
        # auto_now_add timestamps could otherwise be microseconds apart.
        Standup.objects.filter(pk=same_date_first.pk).update(
            created_at=datetime.datetime(2026, 7, 15, 9, 0, tzinfo=datetime.UTC)
        )
        Standup.objects.filter(pk=same_date_second.pk).update(
            created_at=datetime.datetime(2026, 7, 15, 10, 0, tzinfo=datetime.UTC)
        )

        ids = [standup.id for standup in list_standups()]

        self.assertEqual(ids, [same_date_second.id, same_date_first.id, older_date.id])

    def test_avoids_n_plus_one_queries(self):
        for offset in range(3):
            self._create(self.user, datetime.date(2026, 7, 10) - datetime.timedelta(days=offset))

        with self.assertNumQueries(2):
            standups = list(list_standups())
            for standup in standups:
                _ = standup.user.email
                _ = list(standup.items.all())

    def test_empty_database_returns_empty_queryset(self):
        self.assertEqual(list(list_standups()), [])


class ListUserStandupsSelectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="pw")
        self.other = User.objects.create_user(email="other@example.com", password="pw")

    def _create(self, user, standup_date):
        return create_standup(
            user=user,
            validated_data={
                "standup_date": standup_date,
                "blockers": "",
                "items": _valid_items(),
            },
        )

    def test_returns_only_the_users_standups(self):
        self._create(self.user, datetime.date(2026, 7, 13))
        self._create(self.other, datetime.date(2026, 7, 14))

        standups = list(list_user_standups(self.user))

        self.assertEqual([standup.user_id for standup in standups], [self.user.id])

    def test_excludes_other_users_standups(self):
        self._create(self.other, datetime.date(2026, 7, 13))

        self.assertEqual(list(list_user_standups(self.user)), [])

    def test_ordered_by_standup_date_desc_then_created_at_desc(self):
        older = self._create(self.user, datetime.date(2026, 7, 10))
        first = self._create(self.user, datetime.date(2026, 7, 15))
        second = self._create(self.user, datetime.date(2026, 7, 16))

        ids = [standup.id for standup in list_user_standups(self.user)]

        self.assertEqual(ids, [second.id, first.id, older.id])

    def test_empty_result_for_user_with_no_standups(self):
        self.assertEqual(list(list_user_standups(self.user)), [])

    def test_avoids_n_plus_one_queries(self):
        for offset in range(3):
            self._create(self.user, datetime.date(2026, 7, 10) - datetime.timedelta(days=offset))

        with self.assertNumQueries(2):
            standups = list(list_user_standups(self.user))
            for standup in standups:
                _ = standup.user.email
                _ = list(standup.items.all())


class ListWeeklyStandupsSelectorTests(TestCase):
    # A known Monday, so week_start/week_end are unambiguous.
    WEEK_START = datetime.date(2026, 7, 13)
    WEEK_END = datetime.date(2026, 7, 19)

    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="pw", first_name="Jane", last_name="Doe"
        )
        self.other = User.objects.create_user(
            email="other@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )

    def _create(self, user, standup_date):
        return create_standup(
            user=user,
            validated_data={
                "standup_date": standup_date,
                "blockers": "",
                "items": _valid_items(),
            },
        )

    def test_returns_all_standups_within_the_selected_week(self):
        within_start = self._create(self.user, self.WEEK_START)
        within_end = self._create(self.other, self.WEEK_END)

        ids = {standup.id for standup in list_weekly_standups(self.WEEK_START)}

        self.assertEqual(ids, {within_start.id, within_end.id})

    def test_excludes_standups_before_and_after_the_selected_week(self):
        self._create(self.user, self.WEEK_START - datetime.timedelta(days=1))
        self._create(self.other, self.WEEK_END + datetime.timedelta(days=1))

        self.assertEqual(list(list_weekly_standups(self.WEEK_START)), [])

    def test_includes_standups_from_different_users(self):
        self._create(self.user, self.WEEK_START)
        self._create(self.other, self.WEEK_START + datetime.timedelta(days=1))

        emails = {s.user.email for s in list_weekly_standups(self.WEEK_START)}
        self.assertEqual(emails, {"jane@example.com", "other@example.com"})

    def test_ordered_by_standup_date_then_user_name(self):
        later_in_week = self._create(self.user, self.WEEK_START + datetime.timedelta(days=2))
        # Amina Otieno sorts before Jane Doe by first name, same date.
        same_day_amina = self._create(self.other, self.WEEK_START)
        same_day_jane = User.objects.create_user(
            email="jane2@example.com", password="pw", first_name="Zed", last_name="Doe"
        )
        same_day_zed = self._create(same_day_jane, self.WEEK_START)

        ids = [standup.id for standup in list_weekly_standups(self.WEEK_START)]

        self.assertEqual(ids, [same_day_amina.id, same_day_zed.id, later_in_week.id])

    def test_week_with_no_standups_returns_empty_list(self):
        self.assertEqual(list(list_weekly_standups(self.WEEK_START)), [])

    def test_avoids_n_plus_one_queries(self):
        for offset in range(3):
            self._create(self.user, self.WEEK_START + datetime.timedelta(days=offset))

        with self.assertNumQueries(2):
            standups = list(list_weekly_standups(self.WEEK_START))
            for standup in standups:
                _ = standup.user.email
                _ = list(standup.items.all())
