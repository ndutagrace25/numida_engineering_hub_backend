from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.presence.selectors import list_user_presence
from apps.presence.serializers import UserPresenceListSerializer, UserPresenceSerializer
from apps.presence.services import update_user_presence
from common.responses import success_response
from common.schema import AUTHENTICATION_ERROR_RESPONSE, success_envelope

_HEARTBEAT_EXAMPLE = {
    "user": {"id": 12, "first_name": "Grace", "last_name": "Nduta", "display_name": "Grace Nduta"},
    "last_seen_at": "2026-07-16T09:15:00+03:00",
    "status": "ONLINE",
}

_PRESENCE_LIST_EXAMPLE = {
    "online": [
        {
            "user": {
                "id": 12,
                "first_name": "Grace",
                "last_name": "Nduta",
                "display_name": "Grace Nduta",
            },
            "last_seen_at": "2026-07-16T09:15:00+03:00",
        }
    ],
    "recently_active": [],
    "offline": [
        {
            "user": {
                "id": 7,
                "first_name": "Amina",
                "last_name": "Otieno",
                "display_name": "Amina Otieno",
            },
            "last_seen_at": None,
        }
    ],
}


@extend_schema_view(
    post=extend_schema(
        tags=["Presence"],
        operation_id="presenceHeartbeat",
        summary="Send a presence heartbeat",
        description=(
            "Record the authenticated user as active right now. Call this "
            "periodically from the client to keep the user's presence "
            "status current; status (ONLINE/RECENTLY_ACTIVE/OFFLINE) is "
            "always derived from how long ago the last heartbeat was, never "
            "stored directly."
        ),
        request=None,
        examples=[
            OpenApiExample(
                "HeartbeatResponse",
                value={"message": "Presence updated successfully.", "data": _HEARTBEAT_EXAMPLE},
                response_only=True,
                status_codes=["200"],
            ),
        ],
        responses={
            200: success_envelope("HeartbeatResponse", UserPresenceSerializer()),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class HeartbeatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        presence = update_user_presence(user=request.user)

        return success_response(
            data=UserPresenceSerializer(presence).data,
            message="Presence updated successfully.",
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Presence"],
        operation_id="listPresence",
        summary="List user presence",
        description=(
            "Return every active user grouped by current presence status: "
            "online, recently active, or offline. Reflects live state, "
            "derived at request time from each user's last heartbeat — not "
            "a historical record."
        ),
        examples=[
            OpenApiExample(
                "PresenceListResponse",
                value={
                    "message": "User presence retrieved successfully.",
                    "data": _PRESENCE_LIST_EXAMPLE,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        responses={
            200: success_envelope("PresenceListResponse", UserPresenceListSerializer()),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class UserPresenceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grouped = list_user_presence()

        return success_response(
            data=UserPresenceListSerializer(grouped).data,
            message="User presence retrieved successfully.",
        )
