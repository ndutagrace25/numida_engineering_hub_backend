from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.standups.serializers import StandupSerializer


class DashboardSerializer(serializers.Serializer):
    """Shapes the aggregate dict returned by
    apps.dashboard.selectors.get_weekly_dashboard_data() into the response
    body. Not model-backed — output only, never used for input validation.
    """

    week_start = serializers.DateField()
    week_end = serializers.DateField()
    total_active_users = serializers.IntegerField()
    total_submitted_standups = serializers.IntegerField()
    users_who_submitted = UserSerializer(many=True)
    users_who_have_not_submitted = UserSerializer(many=True)
    latest_standups = StandupSerializer(many=True)
