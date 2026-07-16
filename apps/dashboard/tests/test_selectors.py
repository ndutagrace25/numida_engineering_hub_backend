import datetime

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.aob.services import create_aob_item
from apps.dashboard.selectors import get_weekly_dashboard_data
from apps.presence.models import UserPresence
from apps.pto.services import create_pto_entry
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.services import create_pull_request_link
from apps.standups.services import create_standup

# A known Monday, so week boundaries are unambiguous.
WEEK_START = datetime.date(2026, 7, 13)
WEEK_END = datetime.date(2026, 7, 19)
PREVIOUS_WEEK_START = WEEK_START - datetime.timedelta(days=7)


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

    def _create_standup(self, user, standup_date):
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

        self.assertEqual(data["standup_summary"]["total_active_users"], 3)

    def test_counts_submitted_standups_correctly(self):
        self._create_standup(self.grace, WEEK_START)
        self._create_standup(self.amina, WEEK_START + datetime.timedelta(days=1))
        self._create_standup(self.grace, WEEK_START + datetime.timedelta(days=2))  # 2nd, same user

        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual(data["standup_summary"]["total_submitted_standups"], 3)

    def test_returns_users_who_submitted(self):
        self._create_standup(self.grace, WEEK_START)

        data = get_weekly_dashboard_data(WEEK_START)

        ids = [u.id for u in data["standup_summary"]["users_who_submitted"]]
        self.assertEqual(ids, [self.grace.id])

    def test_returns_users_who_have_not_submitted(self):
        self._create_standup(self.grace, WEEK_START)

        data = get_weekly_dashboard_data(WEEK_START)

        ids = {u.id for u in data["standup_summary"]["users_who_have_not_submitted"]}
        self.assertEqual(ids, {self.amina.id, self.zed.id})

    def test_inactive_users_excluded_from_submitted_and_not_submitted(self):
        self._create_standup(self.inactive, WEEK_START)

        data = get_weekly_dashboard_data(WEEK_START)

        listed_ids = {u.id for u in data["standup_summary"]["users_who_submitted"]} | {
            u.id for u in data["standup_summary"]["users_who_have_not_submitted"]
        }
        self.assertNotIn(self.inactive.id, listed_ids)
        # The standup itself still counts toward the raw submission total.
        self.assertEqual(data["standup_summary"]["total_submitted_standups"], 1)

    def test_includes_standups_only_from_the_selected_week(self):
        within = self._create_standup(self.grace, WEEK_START)
        self._create_standup(self.amina, WEEK_START - datetime.timedelta(days=1))
        self._create_standup(self.zed, WEEK_END + datetime.timedelta(days=1))

        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual([s.id for s in data["weekly_standups"]], [within.id])

    def test_week_with_no_standups_returns_valid_empty_data(self):
        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual(data["standup_summary"]["total_submitted_standups"], 0)
        self.assertEqual(list(data["standup_summary"]["users_who_submitted"]), [])
        self.assertEqual(list(data["weekly_standups"]), [])

    def test_includes_aob_items_only_from_the_selected_week(self):
        within = create_aob_item(
            user=self.grace,
            validated_data={
                "title": "Office closed Friday",
                "description": "",
                "external_url": "",
                "week_start": WEEK_START,
                "position": 1,
            },
        )
        create_aob_item(
            user=self.grace,
            validated_data={
                "title": "Other week item",
                "description": "",
                "external_url": "",
                "week_start": PREVIOUS_WEEK_START,
                "position": 1,
            },
        )

        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual([item.id for item in data["aob_items"]], [within.id])

    def test_includes_pull_request_links_only_from_the_selected_week(self):
        within = create_pull_request_link(
            created_by=self.grace,
            validated_data={
                "title": "Fix bug",
                "url": "https://github.com/org/repo/pull/1",
                "group_name": "App PRs",
                "status": PullRequestLink.Status.OPEN,
                "week_start": WEEK_START,
                "position": 1,
            },
        )
        create_pull_request_link(
            created_by=self.grace,
            validated_data={
                "title": "Other week PR",
                "url": "https://github.com/org/repo/pull/2",
                "group_name": "App PRs",
                "status": PullRequestLink.Status.OPEN,
                "week_start": PREVIOUS_WEEK_START,
                "position": 1,
            },
        )

        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual([link.id for link in data["pull_request_links"]], [within.id])

    def test_includes_pto_entries_overlapping_the_selected_week(self):
        # Starts before the week, ends inside it — still overlaps.
        overlapping = create_pto_entry(
            created_by=self.grace,
            validated_data={
                "user": self.grace,
                "start_date": WEEK_START - datetime.timedelta(days=2),
                "end_date": WEEK_START + datetime.timedelta(days=1),
                "reason": "",
                "handover_url": "",
            },
        )
        # Fully outside the week — must be excluded.
        create_pto_entry(
            created_by=self.grace,
            validated_data={
                "user": self.amina,
                "start_date": WEEK_END + datetime.timedelta(days=5),
                "end_date": WEEK_END + datetime.timedelta(days=7),
                "reason": "",
                "handover_url": "",
            },
        )

        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual([entry.id for entry in data["pto_entries"]], [overlapping.id])

    def test_presence_reflects_current_state_not_the_selected_week(self):
        UserPresence.objects.create(user=self.grace, last_seen_at=timezone.now())

        data = get_weekly_dashboard_data(WEEK_START)

        online_user_ids = [entry["user"].id for entry in data["presence"]["online"]]
        self.assertIn(self.grace.id, online_user_ids)

    def test_week_with_no_data_returns_valid_empty_collections(self):
        data = get_weekly_dashboard_data(WEEK_START)

        self.assertEqual(list(data["aob_items"]), [])
        self.assertEqual(list(data["pto_entries"]), [])
        self.assertEqual(list(data["pull_request_links"]), [])
        self.assertEqual(data["presence"]["online"], [])
        self.assertEqual(data["presence"]["recently_active"], [])
        offline_ids = {entry["user"].id for entry in data["presence"]["offline"]}
        self.assertEqual(offline_ids, {self.grace.id, self.amina.id, self.zed.id})

    def test_query_count_does_not_grow_with_more_data(self):
        def _evaluate(data):
            list(data["standup_summary"]["users_who_submitted"])
            list(data["standup_summary"]["users_who_have_not_submitted"])
            for standup in data["weekly_standups"]:
                _ = standup.user.email
                _ = list(standup.items.all())
            list(data["aob_items"])
            list(data["pto_entries"])
            list(data["pull_request_links"])
            list(data["presence"]["online"])
            list(data["presence"]["recently_active"])
            list(data["presence"]["offline"])

        self._create_standup(self.grace, WEEK_START)
        create_aob_item(
            user=self.grace,
            validated_data={
                "title": "Item",
                "description": "",
                "external_url": "",
                "week_start": WEEK_START,
                "position": 1,
            },
        )
        create_pull_request_link(
            created_by=self.grace,
            validated_data={
                "title": "PR",
                "url": "https://github.com/org/repo/pull/1",
                "group_name": "App PRs",
                "status": PullRequestLink.Status.OPEN,
                "week_start": WEEK_START,
                "position": 1,
            },
        )
        create_pto_entry(
            created_by=self.grace,
            validated_data={
                "user": self.grace,
                "start_date": WEEK_START,
                "end_date": WEEK_START,
                "reason": "",
                "handover_url": "",
            },
        )

        with self.assertNumQueries(10):
            _evaluate(get_weekly_dashboard_data(WEEK_START))

        # Add more users/data; the query count must stay the same.
        extra_users = [
            User.objects.create_user(email=f"extra{i}@example.com", password="pw") for i in range(5)
        ]
        for offset, user in enumerate(extra_users):
            self._create_standup(user, WEEK_START + datetime.timedelta(days=offset % 7))
            create_aob_item(
                user=user,
                validated_data={
                    "title": f"Item {offset}",
                    "description": "",
                    "external_url": "",
                    "week_start": WEEK_START,
                    "position": offset + 2,
                },
            )

        with self.assertNumQueries(10):
            _evaluate(get_weekly_dashboard_data(WEEK_START))
