from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.dashboard.selectors import get_weekly_dashboard_data
from apps.dashboard.serializers import DashboardSerializer
from apps.standups.serializers import WeeklyStandupsQuerySerializer
from common.responses import success_response


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Reuses the same week_start validation (required, valid date,
        # must be a Monday) as the standups weekly endpoint.
        query = WeeklyStandupsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        dashboard_data = get_weekly_dashboard_data(query.validated_data["week_start"])

        return success_response(
            data=DashboardSerializer(dashboard_data).data,
            message="Dashboard retrieved successfully.",
        )
