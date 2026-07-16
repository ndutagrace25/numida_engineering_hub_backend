from django.contrib.auth import login, logout
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.selectors import get_active_users
from apps.accounts.serializers import CurrentUserSerializer, LoginSerializer, UserSerializer
from common.responses import success_response
from common.schema import (
    AUTHENTICATION_ERROR_RESPONSE,
    not_found_response,
    null_data_envelope,
    success_envelope,
    validation_error_response,
)

CURRENT_USER_EXAMPLE = {
    "id": 12,
    "email": "grace@example.com",
    "first_name": "Grace",
    "last_name": "Nduta",
    "display_name": "Grace Nduta",
    "is_active": True,
    "date_joined": "2026-01-05T08:30:00+03:00",
}


@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        operation_id="login",
        summary="Log in",
        description=(
            "Authenticate with an email and password and start a session. "
            "The session cookie returned here is required by every other "
            "authenticated endpoint."
        ),
        request=LoginSerializer,
        examples=[
            OpenApiExample(
                "LoginRequest",
                value={"email": "grace@example.com", "password": "correct-horse-battery-staple"},
                request_only=True,
            ),
            OpenApiExample(
                "LoginResponse",
                value={"message": "Login successful.", "data": CURRENT_USER_EXAMPLE},
                response_only=True,
                status_codes=["200"],
            ),
        ],
        responses={
            200: success_envelope("LoginResponse", CurrentUserSerializer()),
            400: validation_error_response(
                "The credentials were missing, malformed, or did not match an active account.",
                {"non_field_errors": ["Unable to log in with the provided credentials."]},
            ),
        },
    ),
)
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


@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        operation_id="logout",
        summary="Log out",
        description="End the authenticated user's session.",
        request=None,
        examples=[
            OpenApiExample(
                "LogoutResponse",
                value={"message": "Logout successful.", "data": None},
                response_only=True,
                status_codes=["200"],
            ),
        ],
        responses={
            200: null_data_envelope("LogoutResponse"),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class LogoutView(APIView):
    # Explicit even though it matches the global default: logging out
    # requires being logged in, so an unauthenticated caller gets a clean
    # 401 rather than a no-op 200.
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return success_response(data=None, message="Logout successful.")


@extend_schema_view(
    get=extend_schema(
        tags=["Authentication"],
        operation_id="currentUser",
        summary="Get the current user",
        description="Return the profile of the currently authenticated user.",
        examples=[
            OpenApiExample(
                "CurrentUserResponse",
                value={
                    "message": "Current user retrieved successfully.",
                    "data": CURRENT_USER_EXAMPLE,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
        responses={
            200: success_envelope("CurrentUserResponse", CurrentUserSerializer()),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(
            data=CurrentUserSerializer(request.user).data,
            message="Current user retrieved successfully.",
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Users"],
        operation_id="listUsers",
        summary="List users",
        description=(
            "List active users, searchable by first name, last name, or email. "
            "Inactive users are never returned."
        ),
        responses={
            200: UserSerializer(many=True),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    filter_backends = [SearchFilter]
    search_fields = ["first_name", "last_name", "email"]

    def get_queryset(self):
        return get_active_users()


@extend_schema_view(
    get=extend_schema(
        tags=["Users"],
        operation_id="retrieveUser",
        summary="Retrieve a user",
        description=(
            "Retrieve a single active user by id. Inactive users 404 the same "
            "way a nonexistent id would, so their existence isn't leaked."
        ),
        responses={
            200: success_envelope("UserResponse", UserSerializer()),
            401: AUTHENTICATION_ERROR_RESPONSE,
            404: not_found_response("user"),
        },
    ),
)
class UserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        return get_active_users()

    def retrieve(self, request, *args, **kwargs):
        # get_object() 404s automatically for a missing pk or a pk outside
        # get_queryset() (i.e. an inactive user) — both look identical to the
        # caller, which is correct: existence of inactive accounts shouldn't
        # be leaked.
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message="User retrieved successfully.",
        )
