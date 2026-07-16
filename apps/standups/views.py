from django.db import IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.standups.filters import StandupFilter
from apps.standups.models import Standup
from apps.standups.permissions import IsStandupOwner
from apps.standups.selectors import (
    get_standup_by_id,
    list_standups,
    list_user_standups,
    list_weekly_standups,
)
from apps.standups.serializers import StandupSerializer, WeeklyStandupsQuerySerializer
from apps.standups.services import create_standup, delete_standup, update_standup
from common.responses import created_response, success_response
from common.schema import (
    AUTHENTICATION_ERROR_RESPONSE,
    not_found_response,
    null_data_envelope,
    permission_error_response,
    success_envelope,
    validation_error_response,
)

DUPLICATE_STANDUP_DATE_ERROR = {
    "standup_date": ["A standup for this date has already been submitted."]
}

_ITEMS_REQUEST_EXAMPLE = [
    {"section": "COMPLETED", "content": "Shipped the login page.", "position": 1},
    {"section": "CURRENT", "content": "Working on the dashboard.", "position": 1},
    {"section": "PLANNED", "content": "Start on the PR review flow.", "position": 1},
]

_STANDUP_EXAMPLE = {
    "id": 101,
    "user": {
        "id": 12,
        "email": "grace@example.com",
        "first_name": "Grace",
        "last_name": "Nduta",
        "display_name": "Grace Nduta",
        "is_active": True,
        "date_joined": "2026-01-05T08:30:00+03:00",
    },
    "standup_date": "2026-07-13",
    "blockers": "",
    "items": [
        {
            "id": 501,
            "section": "COMPLETED",
            "content": "Shipped the login page.",
            "position": 1,
            "created_at": "2026-07-13T09:00:00+03:00",
            "updated_at": "2026-07-13T09:00:00+03:00",
        },
        {
            "id": 502,
            "section": "CURRENT",
            "content": "Working on the dashboard.",
            "position": 1,
            "created_at": "2026-07-13T09:00:00+03:00",
            "updated_at": "2026-07-13T09:00:00+03:00",
        },
        {
            "id": 503,
            "section": "PLANNED",
            "content": "Start on the PR review flow.",
            "position": 1,
            "created_at": "2026-07-13T09:00:00+03:00",
            "updated_at": "2026-07-13T09:00:00+03:00",
        },
    ],
    "created_at": "2026-07-13T09:00:00+03:00",
    "updated_at": "2026-07-13T09:00:00+03:00",
}

_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "CreateStandupRequest",
    value={"standup_date": "2026-07-13", "blockers": "", "items": _ITEMS_REQUEST_EXAMPLE},
    request_only=True,
)

_STANDUP_VALIDATION_ERROR_RESPONSE = validation_error_response(
    "standup_date is missing/invalid, a required section (COMPLETED, CURRENT, PLANNED) has no "
    "items, or a standup for this date already exists.",
    {"items": ["At least one item is required for: PLANNED."]},
)

# Built once and reused across every action that returns this shape (create,
# retrieve, update) — calling success_envelope() again per-action would
# produce distinct dynamic classes that happen to share a name, which
# drf-spectacular flags as a component collision.
_STANDUP_RESPONSE = success_envelope("StandupResponse", StandupSerializer())


@extend_schema_view(
    get=extend_schema(
        tags=["Standups"],
        operation_id="listStandups",
        summary="List standups",
        description=(
            "List every user's standups, newest first. Supports filtering by "
            "user, standup_date, a date_after/date_before range, and section, "
            "plus free-text search across the author's name, item content, "
            "and blockers."
        ),
        responses={
            200: StandupSerializer(many=True),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
    post=extend_schema(
        tags=["Standups"],
        operation_id="createStandup",
        summary="Submit a standup",
        description=(
            "Submit a standup for the authenticated user, with its nested "
            "items (at least one each of COMPLETED, CURRENT, and PLANNED). "
            "Only one standup per user per standup_date is allowed."
        ),
        examples=[
            _CREATE_REQUEST_EXAMPLE,
            OpenApiExample(
                "CreateStandupResponse",
                value={"message": "Standup submitted successfully.", "data": _STANDUP_EXAMPLE},
                response_only=True,
                status_codes=["201"],
            ),
        ],
        responses={
            201: _STANDUP_RESPONSE,
            400: _STANDUP_VALIDATION_ERROR_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class StandupListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StandupSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = StandupFilter
    search_fields = ["user__first_name", "user__last_name", "items__content", "blockers"]

    def get_queryset(self):
        return list_standups()

    def get(self, request, *args, **kwargs):
        # Filtering/searching through items (section, search) joins to a
        # to-many relation, which can multiply rows — distinct() collapses
        # those back to one row per matching standup before pagination.
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = StandupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            standup = create_standup(user=request.user, validated_data=serializer.validated_data)
        except IntegrityError as exc:
            # The model's UniqueConstraint(user, standup_date) is the source
            # of truth for this rule; translate it into the standard error
            # format instead of letting it surface as an unhandled 500.
            raise ValidationError(DUPLICATE_STANDUP_DATE_ERROR) from exc

        return created_response(
            data=StandupSerializer(standup).data,
            message="Standup submitted successfully.",
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Standups"],
        operation_id="myStandups",
        summary="List my standups",
        description="List the authenticated user's own standups, newest first.",
        responses={
            200: StandupSerializer(many=True),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class MyStandupsListView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StandupSerializer

    def get_queryset(self):
        # drf-spectacular introspects get_queryset() at schema-generation
        # time with an AnonymousUser, which list_user_standups() can't
        # filter by — swagger_fake_view is the standard escape hatch for
        # that case and never true for a real request.
        if getattr(self, "swagger_fake_view", False):
            return Standup.objects.none()
        return list_user_standups(self.request.user)

    def get(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        tags=["Standups"],
        operation_id="weeklyStandups",
        summary="List standups for a week",
        description=(
            "List every user's standups for a single week (Monday through "
            "Sunday). Not paginated — a week's worth of standups is the "
            "entire, intentionally bounded result set."
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
        responses={
            200: success_envelope("WeeklyStandupsResponse", StandupSerializer(many=True)),
            400: validation_error_response(
                "week_start is missing, not a valid date, or not a Monday.",
                {"week_start": ["Date must fall on a Monday."]},
            ),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class WeeklyStandupsListView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StandupSerializer
    # Never paginated by design (see the docstring below) — set explicitly
    # so the documented response shape matches actual behavior instead of
    # assuming pagination just because a pagination_class is configured
    # project-wide.
    pagination_class = None

    def get(self, request, *args, **kwargs):
        query = WeeklyStandupsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        standups = list_weekly_standups(query.validated_data["week_start"])

        # No pagination here — a single week's worth of standups is the
        # entire, intentionally bounded result set.
        return success_response(
            data=StandupSerializer(standups, many=True).data,
            message="Weekly standups retrieved successfully.",
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Standups"],
        operation_id="retrieveStandup",
        summary="Retrieve a standup",
        description="Retrieve a single standup by id, with its nested items.",
        responses={
            200: _STANDUP_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
            404: not_found_response("standup"),
        },
    ),
    patch=extend_schema(
        tags=["Standups"],
        operation_id="updateStandup",
        summary="Update a standup",
        description=(
            "Partially update a standup. Only the owner may update it. "
            "Omitting `items` leaves existing items untouched; including it "
            "replaces the full set and re-validates that every required "
            "section is still represented."
        ),
        examples=[
            OpenApiExample(
                "UpdateStandupRequest",
                value={"blockers": "Waiting on the staging database to be restored."},
                request_only=True,
            ),
        ],
        responses={
            200: _STANDUP_RESPONSE,
            400: _STANDUP_VALIDATION_ERROR_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
            403: permission_error_response("You do not have permission to perform this action."),
            404: not_found_response("standup"),
        },
    ),
    delete=extend_schema(
        tags=["Standups"],
        operation_id="deleteStandup",
        summary="Delete a standup",
        description="Delete a standup. Only the owner may delete it.",
        responses={
            200: null_data_envelope("DeleteStandupResponse"),
            401: AUTHENTICATION_ERROR_RESPONSE,
            403: permission_error_response("You do not have permission to perform this action."),
            404: not_found_response("standup"),
        },
    ),
)
class StandupDetailView(generics.GenericAPIView):
    # IsStandupOwner (IsOwnerOrReadOnly under the hood) allows safe methods
    # for anyone and only restricts unsafe methods to the owner — exactly
    # "anyone can view, only the owner can update/delete", with no extra
    # method-specific branching needed here.
    permission_classes = [IsAuthenticated, IsStandupOwner]
    queryset = Standup.objects.all()
    serializer_class = StandupSerializer

    def get(self, request, *args, **kwargs):
        # Bypasses get_object()'s plain queryset in favor of the selector's
        # select_related/prefetch_related-optimized one, but still runs the
        # same object-level permission check get_object() would have.
        standup = get_standup_by_id(kwargs["pk"])
        self.check_object_permissions(request, standup)

        return success_response(
            data=StandupSerializer(standup).data,
            message="Standup retrieved successfully.",
        )

    def patch(self, request, *args, **kwargs):
        # get_object() 404s for a nonexistent pk and, via
        # check_object_permissions(), 403s for a pk that exists but isn't
        # owned by request.user.
        standup = self.get_object()

        serializer = self.get_serializer(standup, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated = update_standup(standup=standup, validated_data=serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError(DUPLICATE_STANDUP_DATE_ERROR) from exc

        return success_response(
            data=StandupSerializer(updated).data,
            message="Standup updated successfully.",
        )

    def delete(self, request, *args, **kwargs):
        standup = self.get_object()

        delete_standup(standup=standup)

        return success_response(data=None, message="Standup deleted successfully.")
