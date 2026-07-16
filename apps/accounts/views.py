from django.contrib.auth import login, logout
from rest_framework import generics
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.selectors import get_active_users
from apps.accounts.serializers import CurrentUserSerializer, LoginSerializer, UserSerializer
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


class LogoutView(APIView):
    # Explicit even though it matches the global default: logging out
    # requires being logged in, so an unauthenticated caller gets a clean
    # 401 rather than a no-op 200.
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return success_response(data=None, message="Logout successful.")


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(
            data=CurrentUserSerializer(request.user).data,
            message="Current user retrieved successfully.",
        )


class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    filter_backends = [SearchFilter]
    search_fields = ["first_name", "last_name", "email"]

    def get_queryset(self):
        return get_active_users()
