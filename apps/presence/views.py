from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.presence.serializers import UserPresenceSerializer
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
