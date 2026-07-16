import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.dashboard.selectors import get_weekly_dashboard_data
from apps.standups.services import create_standup

# A known Monday, so week boundaries are unambiguous.
WEEK_START = datetime.date(2026, 7, 13)
WEEK_END = datetime.date(2026, 7, 19)


def _valid_items():
    return [
        {"section": "COMPLETED", "content": "Shipped X.", "position": 1},
        {"section": "CURRENT", "content": "Working on Y.", "position": 1},
        {"section": "PLANNED", "content": "Plan Z.", "position": 1},
    ]


class GetWeeklyDashboardDataTests(TestCase):
    def setUp(self):
        self.grace = User.objects.create_user(
            email="grace@example.com", password="pw", first_name="Grace", last_name="Nduta"
        )
        self.amina = User.objects.create_user(
            email="amina@example.com", password="pw", first_name="Amina", last_name="Otieno"
        )
        self.zed = User.objects.create_user(
            email="zed@example.com", password="pw", first_name="Zed", last_name="Smith"
        )
        self.inactive = User.objects.create_user(
            email="inactive@example.com",
            password="pw",
            first_name="In",
            last_name="Active",
            is_active=False,
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

    def test_returns_correct_week_boundaries(self):
        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual(data["week_start"], WEEK_START)
        self.assertEqual(data["week_end"], WEEK_END)

    def test_counts_only_active_users(self):
        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual(data["total_active_users"], 3)

    def test_counts_submitted_standups_correctly(self):
        self._create(self.grace, WEEK_START)
        self._create(self.amina, WEEK_START + datetime.timedelta(days=1))
        self._create(self.grace, WEEK_START + datetime.timedelta(days=2))  # 2nd, same user

        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual(data["total_submitted_standups"], 3)

    def test_returns_users_who_submitted(self):
        self._create(self.grace, WEEK_START)

        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual([u.id for u in data["users_who_submitted"]], [self.grace.id])

    def test_returns_users_who_have_not_submitted(self):
        self._create(self.grace, WEEK_START)

        data = get_weekly_dashboard_data(WEEK_START)

        ids = {u.id for u in data["users_who_have_not_submitted"]}
        self.assertEqual(ids, {self.amina.id, self.zed.id})

    def test_inactive_users_excluded_from_submitted_and_not_submitted(self):
        self._create(self.inactive, WEEK_START)

        data = get_weekly_dashboard_data(WEEK_START)

        listed_ids = {u.id for u in data["users_who_submitted"]} | {
            u.id for u in data["users_who_have_not_submitted"]
        }
        self.assertNotIn(self.inactive.id, listed_ids)
        # The standup itself still counts toward the raw submission total.
        self.assertEqual(data["total_submitted_standups"], 1)

    def test_includes_standups_only_from_the_selected_week(self):
        within = self._create(self.grace, WEEK_START)
        self._create(self.amina, WEEK_START - datetime.timedelta(days=1))
        self._create(self.zed, WEEK_END + datetime.timedelta(days=1))

        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual([s.id for s in data["latest_standups"]], [within.id])

    def test_week_with_no_standups_returns_valid_empty_data(self):
        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual(data["total_submitted_standups"], 0)
        self.assertEqual(list(data["users_who_submitted"]), [])
        self.assertEqual(list(data["latest_standups"]), [])

    def test_query_count_does_not_grow_with_more_data(self):
        def _evaluate(data):
            list(data["users_who_submitted"])
            list(data["users_who_have_not_submitted"])
            for standup in data["latest_standups"]:
                _ = standup.user.email
                _ = list(standup.items.all())

        self._create(self.grace, WEEK_START)

        with self.assertNumQueries(6):
            _evaluate(get_weekly_dashboard_data(WEEK_START))

        # Add more users and standups; the query count must stay the same.
        extra_users = [
            User.objects.create_user(email=f"extra{i}@example.com", password="pw") for i in range(5)
        ]
        for offset, user in enumerate(extra_users):
            self._create(user, WEEK_START + datetime.timedelta(days=offset % 7))

        with self.assertNumQueries(6):
            _evaluate(get_weekly_dashboard_data(WEEK_START))
