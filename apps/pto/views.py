from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.pto.filters import PTOEntryFilter
from apps.pto.models import PTOEntry
from apps.pto.permissions import IsPTOEntryCreator
from apps.pto.selectors import get_pto_entry_by_id, list_pto_entries
from apps.pto.serializers import PTOEntrySerializer
from apps.pto.services import create_pto_entry, delete_pto_entry, update_pto_entry
from common.responses import created_response, success_response
from common.schema import (
    AUTHENTICATION_ERROR_RESPONSE,
    not_found_response,
    null_data_envelope,
    permission_error_response,
    success_envelope,
    validation_error_response,
)

_PTO_ENTRY_EXAMPLE = {
    "id": 33,
    "user": {
        "id": 12,
        "first_name": "Grace",
        "last_name": "Nduta",
        "display_name": "Grace Nduta",
    },
    "start_date": "2026-07-20",
    "end_date": "2026-07-24",
    "reason": "Annual leave",
    "handover_url": "https://docs.example.com/handover/grace-july",
    "created_by": {
        "id": 12,
        "first_name": "Grace",
        "last_name": "Nduta",
        "display_name": "Grace Nduta",
    },
    "created_at": "2026-07-13T09:00:00+03:00",
    "updated_at": "2026-07-13T09:00:00+03:00",
}

_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "CreatePTORequest",
    value={
        "user": 12,
        "start_date": "2026-07-20",
        "end_date": "2026-07-24",
        "reason": "Annual leave",
        "handover_url": "https://docs.example.com/handover/grace-july",
    },
    request_only=True,
)

_PTO_VALIDATION_ERROR_RESPONSE = validation_error_response(
    "end_date is earlier than start_date, or handover_url is not HTTPS.",
    {"end_date": ["End date cannot be earlier than start date."]},
)

# Built once and reused across every action that returns this shape
# (create, retrieve, update) — calling success_envelope() again per-action
# would produce distinct dynamic classes that happen to share a name,
# which drf-spectacular flags as a component collision.
_PTO_ENTRY_RESPONSE = success_envelope("PTOEntryResponse", PTOEntrySerializer())


@extend_schema_view(
    get=extend_schema(
        tags=["PTO"],
        operation_id="listPTO",
        summary="List PTO entries",
        description=(
            "List PTO entries, soonest start_date first. Supports filtering "
            "by user, creator, start_date/end_date, a date_after/date_before "
            "range on start_date, and active_on (entries covering a single "
            "date), plus free-text search across the PTO-taker's name and "
            "reason."
        ),
        responses={
            200: PTOEntrySerializer(many=True),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
    post=extend_schema(
        tags=["PTO"],
        operation_id="createPTO",
        summary="Create a PTO entry",
        description=(
            "Log a PTO entry. `user` (who is taking the leave) is passed as "
            "a plain id and may be a different person than the "
            "authenticated creator — e.g. logging leave on someone's behalf."
        ),
        examples=[
            _CREATE_REQUEST_EXAMPLE,
            OpenApiExample(
                "CreatePTOResponse",
                value={"message": "PTO entry created successfully.", "data": _PTO_ENTRY_EXAMPLE},
                response_only=True,
                status_codes=["201"],
            ),
        ],
        responses={
            201: _PTO_ENTRY_RESPONSE,
            400: _PTO_VALIDATION_ERROR_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class PTOEntryListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PTOEntrySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = PTOEntryFilter
    search_fields = ["user__first_name", "user__last_name", "reason"]

    def get_queryset(self):
        return list_pto_entries()

    def get(self, request, *args, **kwargs):
        # user/created_by are forward to-one FKs, so none of these
        # filters/search fields can join to a to-many relation — rows
        # can't be multiplied, so distinct() would only add an
        # unnecessary sort/uniqueness step.
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = PTOEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry = create_pto_entry(created_by=request.user, validated_data=serializer.validated_data)

        return created_response(
            data=PTOEntrySerializer(entry).data,
            message="PTO entry created successfully.",
        )


@extend_schema_view(
    get=extend_schema(
        tags=["PTO"],
        operation_id="retrievePTO",
        summary="Retrieve a PTO entry",
        description="Retrieve a single PTO entry by id.",
        responses={
            200: _PTO_ENTRY_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
            404: not_found_response("PTO entry"),
        },
    ),
    patch=extend_schema(
        tags=["PTO"],
        operation_id="updatePTO",
        summary="Update a PTO entry",
        description="Partially update a PTO entry. Only the creator may update it.",
        examples=[
            OpenApiExample(
                "UpdatePTORequest",
                value={"end_date": "2026-07-25"},
                request_only=True,
            ),
        ],
        responses={
            200: _PTO_ENTRY_RESPONSE,
            400: _PTO_VALIDATION_ERROR_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
            403: permission_error_response("You do not have permission to perform this action."),
            404: not_found_response("PTO entry"),
        },
    ),
    delete=extend_schema(
        tags=["PTO"],
        operation_id="deletePTO",
        summary="Delete a PTO entry",
        description="Delete a PTO entry. Only the creator may delete it.",
        responses={
            200: null_data_envelope("DeletePTOResponse"),
            401: AUTHENTICATION_ERROR_RESPONSE,
            403: permission_error_response("You do not have permission to perform this action."),
            404: not_found_response("PTO entry"),
        },
    ),
)
class PTOEntryDetailView(generics.GenericAPIView):
    # IsPTOEntryCreator (IsOwnerOrReadOnly with owner_field="created_by")
    # allows safe methods for anyone and restricts unsafe methods to the
    # creator — matching the same reuse already established for standups
    # and AOB items.
    permission_classes = [IsAuthenticated, IsPTOEntryCreator]
    # select_related("user", "created_by") backs self.get_object() for
    # PATCH/DELETE (GET bypasses it via get_pto_entry_by_id()'s own
    # select_related) — avoids extra queries when the permission check or
    # response serialization reads either FK. Safe even though
    # update_pto_entry() can reassign "user": DRF's PrimaryKeyRelatedField
    # resolves it to a full User instance, and a direct attribute
    # assignment correctly replaces the cached object rather than leaving
    # a stale one.
    queryset = PTOEntry.objects.select_related("user", "created_by")
    serializer_class = PTOEntrySerializer

    def get(self, request, *args, **kwargs):
        # Bypasses get_object()'s plain queryset in favor of the selector's
        # select_related-optimized one, but still runs the same
        # object-level permission check get_object() would have (a no-op
        # here, since GET is a safe method IsOwnerOrReadOnly allows anyone).
        entry = get_pto_entry_by_id(kwargs["pk"])
        self.check_object_permissions(request, entry)

        return success_response(
            data=PTOEntrySerializer(entry).data,
            message="PTO entry retrieved successfully.",
        )

    def patch(self, request, *args, **kwargs):
        # get_object() 404s for a nonexistent pk and, via
        # check_object_permissions(), 403s for a pk that exists but wasn't
        # created by request.user.
        entry = self.get_object()

        serializer = self.get_serializer(entry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = update_pto_entry(entry=entry, validated_data=serializer.validated_data)

        return success_response(
            data=PTOEntrySerializer(updated).data,
            message="PTO entry updated successfully.",
        )

    def delete(self, request, *args, **kwargs):
        entry = self.get_object()

        delete_pto_entry(entry=entry)

        return success_response(data=None, message="PTO entry deleted successfully.")
