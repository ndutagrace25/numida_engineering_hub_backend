from rest_framework import serializers

from apps.accounts.serializers import MinimalUserSerializer
from apps.aob.serializers import AOBItemSerializer
from apps.presence.serializers import UserPresenceListSerializer
from apps.pto.serializers import PTOEntrySerializer
from apps.pull_requests.serializers import PullRequestLinkSerializer
from apps.standups.serializers import StandupSerializer


class StandupSummarySerializer(serializers.Serializer):
    total_active_users = serializers.IntegerField()
    total_submitted_standups = serializers.IntegerField()
    users_who_submitted = MinimalUserSerializer(many=True)
    users_who_have_not_submitted = MinimalUserSerializer(many=True)


class DashboardSerializer(serializers.Serializer):
    """Shapes the aggregate dict returned by
    apps.dashboard.selectors.get_weekly_dashboard_data() into the response
    body. Not model-backed — output only, never used for input validation.

    Every nested field reuses its owning module's existing serializer
    as-is rather than duplicating field lists here — including
    StandupSerializer for weekly_standups, whose nested `user` uses the
    full UserSerializer (not MinimalUserSerializer) upstream, so it
    exposes more fields than aob_items/pto_entries/pull_request_links'
    creator fields do. That's an accepted reuse trade-off, not an
    oversight.
    """

    week_start = serializers.DateField()
    week_end = serializers.DateField()
    standup_summary = StandupSummarySerializer()
    weekly_standups = StandupSerializer(many=True)
    presence = UserPresenceListSerializer()
    aob_items = AOBItemSerializer(many=True)
    pto_entries = PTOEntrySerializer(many=True)
    pull_request_links = PullRequestLinkSerializer(many=True)
