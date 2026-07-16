from django.contrib.auth import login
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.serializers import CurrentUserSerializer, LoginSerializer
from common.responses import success_response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Django's login() already handles re-authenticating an already
        # logged-in user safely (it flushes the session first if the user
        # differs, and leaves it alone if it's the same user).
        login(request, user)

        return success_response(
            data=CurrentUserSerializer(user).data,
            message="Login successful.",
        )
