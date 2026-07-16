from django.db import IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
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

DUPLICATE_STANDUP_DATE_ERROR = {
    "standup_date": ["A standup for this date has already been submitted."]
}


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


class MyStandupsListView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StandupSerializer

    def get_queryset(self):
        return list_user_standups(self.request.user)

    def get(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class WeeklyStandupsListView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StandupSerializer

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
