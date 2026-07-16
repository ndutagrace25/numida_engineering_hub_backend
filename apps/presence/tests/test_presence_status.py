import datetime

from django.test import TestCase
from django.utils import timezone

from apps.presence.models import PresenceStatus, get_presence_status


class GetPresenceStatusTests(TestCase):
    def test_recent_timestamp_returns_online(self):
        last_seen_at = timezone.now() - datetime.timedelta(seconds=30)

        self.assertEqual(get_presence_status(last_seen_at), PresenceStatus.ONLINE)

    def test_just_under_two_minutes_ago_returns_online(self):
        # get_presence_status() recomputes timezone.now() internally, so
        # testing the *exact* boundary is racy against the test's own
        # execution time — stay just inside it instead.
        last_seen_at = timezone.now() - datetime.timedelta(minutes=1, seconds=55)

        self.assertEqual(get_presence_status(last_seen_at), PresenceStatus.ONLINE)

    def test_timestamp_between_two_and_fifteen_minutes_returns_recently_active(self):
        last_seen_at = timezone.now() - datetime.timedelta(minutes=10)

        self.assertEqual(get_presence_status(last_seen_at), PresenceStatus.RECENTLY_ACTIVE)

    def test_just_under_fifteen_minutes_ago_returns_recently_active(self):
        last_seen_at = timezone.now() - datetime.timedelta(minutes=14, seconds=55)

        self.assertEqual(get_presence_status(last_seen_at), PresenceStatus.RECENTLY_ACTIVE)

    def test_older_timestamp_returns_offline(self):
        last_seen_at = timezone.now() - datetime.timedelta(minutes=20)

        self.assertEqual(get_presence_status(last_seen_at), PresenceStatus.OFFLINE)
