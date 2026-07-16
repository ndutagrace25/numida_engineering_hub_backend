from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.presence.selectors import list_user_presence
from apps.presence.serializers import UserPresenceListSerializer, UserPresenceSerializer
from apps.presence.services import update_user_presence
from common.responses import success_response


class HeartbeatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        presence = update_user_presence(user=request.user)

        return success_response(
            data=UserPresenceSerializer(presence).data,
            message="Presence updated successfully.",
        )


class UserPresenceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grouped = list_user_presence()

        return success_response(
            data=UserPresenceListSerializer(grouped).data,
            message="User presence retrieved successfully.",
        )
