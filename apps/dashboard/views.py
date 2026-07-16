from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.dashboard.selectors import get_weekly_dashboard_data
from apps.dashboard.serializers import DashboardSerializer
from apps.standups.serializers import WeeklyStandupsQuerySerializer
from common.responses import success_response
from common.schema import AUTHENTICATION_ERROR_RESPONSE, success_envelope, validation_error_response

_DASHBOARD_EXAMPLE = {
    "week_start": "2026-07-13",
    "week_end": "2026-07-19",
    "standup_summary": {
        "total_active_users": 12,
        "total_submitted_standups": 9,
        "users_who_submitted": [
            {"id": 12, "first_name": "Grace", "last_name": "Nduta", "display_name": "Grace Nduta"}
        ],
        "users_who_have_not_submitted": [
            {"id": 7, "first_name": "Amina", "last_name": "Otieno", "display_name": "Amina Otieno"}
        ],
    },
    "weekly_standups": [],
    "presence": {"online": [], "recently_active": [], "offline": []},
    "aob_items": [],
    "pto_entries": [],
    "pull_request_links": [],
}


@extend_schema_view(
    get=extend_schema(
        tags=["Dashboard"],
        operation_id="dashboard",
        summary="Get the weekly dashboard",
        description=(
            "Aggregate read-only view of a single week: standup submission "
            "totals, that week's standups, current presence, AOB items, PTO "
            "overlapping the week, and pull request links for the week. "
            "Nothing here is written by this endpoint — it only reuses each "
            "module's own selectors."
        ),
        parameters=[
            OpenApiParameter(
                name="week_start",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="The Monday that starts the target week, as YYYY-MM-DD.",
            ),
        ],
        examples=[
            OpenApiExample(
                "DashboardResponse",
                value={
                    "message": "Dashboard retrieved successfully.",
                    "data": _DASHBOARD_EXAMPLE,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        responses={
            200: success_envelope("DashboardResponse", DashboardSerializer()),
            400: validation_error_response(
                "week_start is missing, not a valid date, or not a Monday.",
                {"week_start": ["Date must fall on a Monday."]},
            ),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
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
