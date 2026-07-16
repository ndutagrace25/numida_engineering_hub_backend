from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.aob.filters import AOBItemFilter
from apps.aob.models import AOBItem
from apps.aob.permissions import IsAOBItemCreator
from apps.aob.selectors import get_aob_item_by_id, list_aob_items
from apps.aob.serializers import AOBItemSerializer
from apps.aob.services import create_aob_item, delete_aob_item, update_aob_item
from common.responses import created_response, success_response
from common.schema import (
    AUTHENTICATION_ERROR_RESPONSE,
    not_found_response,
    null_data_envelope,
    permission_error_response,
    success_envelope,
    validation_error_response,
)

_AOB_ITEM_EXAMPLE = {
    "id": 21,
    "title": "Office closed Friday",
    "description": "The office will be closed for a public holiday.",
    "external_url": "",
    "week_start": "2026-07-13",
    "position": 1,
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
    "CreateAOBRequest",
    value={
        "title": "Office closed Friday",
        "description": "The office will be closed for a public holiday.",
        "external_url": "",
        "week_start": "2026-07-13",
        "position": 1,
    },
    request_only=True,
)

_AOB_VALIDATION_ERROR_RESPONSE = validation_error_response(
    "title is blank, external_url is not HTTPS, or week_start does not fall on a Monday.",
    {"week_start": ["Date must fall on a Monday."]},
)

# Built once and reused across every action that returns this shape
# (create, retrieve, update) — calling success_envelope() again per-action
# would produce distinct dynamic classes that happen to share a name,
# which drf-spectacular flags as a component collision.
_AOB_ITEM_RESPONSE = success_envelope("AOBItemResponse", AOBItemSerializer())


@extend_schema_view(
    get=extend_schema(
        tags=["AOB"],
        operation_id="listAOB",
        summary="List AOB items",
        description=(
            "List any-other-business items across all weeks, newest week "
            "first. Supports filtering by week_start, a week_after/"
            "week_before range, and creator, plus free-text search across "
            "title, description, and creator name."
        ),
        responses={
            200: AOBItemSerializer(many=True),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
    post=extend_schema(
        tags=["AOB"],
        operation_id="createAOB",
        summary="Create an AOB item",
        description="Create an any-other-business item for a given week.",
        examples=[
            _CREATE_REQUEST_EXAMPLE,
            OpenApiExample(
                "CreateAOBResponse",
                value={"message": "AOB item created successfully.", "data": _AOB_ITEM_EXAMPLE},
                response_only=True,
                status_codes=["201"],
            ),
        ],
        responses={
            201: _AOB_ITEM_RESPONSE,
            400: _AOB_VALIDATION_ERROR_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
class AOBItemListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AOBItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AOBItemFilter
    search_fields = ["title", "description", "created_by__first_name", "created_by__last_name"]

    def get_queryset(self):
        return list_aob_items()

    def get(self, request, *args, **kwargs):
        # created_by is a forward, to-one FK — unlike standups' items,
        # none of these filters/search fields can join to a to-many
        # relation, so rows can't be multiplied and distinct() would only
        # add an unnecessary sort/uniqueness step. Revisit if a to-many
        # field is ever added to search_fields.
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = AOBItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item = create_aob_item(user=request.user, validated_data=serializer.validated_data)

        return created_response(
            data=AOBItemSerializer(item).data,
            message="AOB item created successfully.",
        )


@extend_schema_view(
    get=extend_schema(
        tags=["AOB"],
        operation_id="retrieveAOB",
        summary="Retrieve an AOB item",
        description="Retrieve a single AOB item by id.",
        responses={
            200: _AOB_ITEM_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
            404: not_found_response("AOB item"),
        },
    ),
    patch=extend_schema(
        tags=["AOB"],
        operation_id="updateAOB",
        summary="Update an AOB item",
        description="Partially update an AOB item. Only the creator may update it.",
        examples=[
            OpenApiExample(
                "UpdateAOBRequest",
                value={"description": "Updated: the office reopens Monday."},
                request_only=True,
            ),
        ],
        responses={
            200: _AOB_ITEM_RESPONSE,
            400: _AOB_VALIDATION_ERROR_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
            403: permission_error_response("You do not have permission to perform this action."),
            404: not_found_response("AOB item"),
        },
    ),
    delete=extend_schema(
        tags=["AOB"],
        operation_id="deleteAOB",
        summary="Delete an AOB item",
        description="Delete an AOB item. Only the creator may delete it.",
        responses={
            200: null_data_envelope("DeleteAOBResponse"),
            401: AUTHENTICATION_ERROR_RESPONSE,
            403: permission_error_response("You do not have permission to perform this action."),
            404: not_found_response("AOB item"),
        },
    ),
)
class AOBItemDetailView(generics.GenericAPIView):
    # IsAOBItemCreator (IsOwnerOrReadOnly with owner_field="created_by")
    # allows safe methods for anyone and restricts unsafe methods to the
    # creator — matching the same reuse already established for standups.
    permission_classes = [IsAuthenticated, IsAOBItemCreator]
    # select_related("created_by") backs self.get_object() for PATCH/
    # DELETE (GET bypasses it via get_aob_item_by_id()'s own
    # select_related) — avoids a second query when the permission check
    # or response serialization reads created_by. Safe since created_by
    # is never reassigned by update_aob_item().
    queryset = AOBItem.objects.select_related("created_by")
    serializer_class = AOBItemSerializer

    def get(self, request, *args, **kwargs):
        # Bypasses get_object()'s plain queryset in favor of the selector's
        # select_related-optimized one, but still runs the same
        # object-level permission check get_object() would have (a no-op
        # here, since GET is a safe method IsOwnerOrReadOnly allows anyone).
        item = get_aob_item_by_id(kwargs["pk"])
        self.check_object_permissions(request, item)

        return success_response(
            data=AOBItemSerializer(item).data,
            message="AOB item retrieved successfully.",
        )

    def patch(self, request, *args, **kwargs):
        # get_object() 404s for a nonexistent pk and, via
        # check_object_permissions(), 403s for a pk that exists but wasn't
        # created by request.user.
        item = self.get_object()

        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = update_aob_item(item=item, validated_data=serializer.validated_data)

        return success_response(
            data=AOBItemSerializer(updated).data,
            message="AOB item updated successfully.",
        )

    def delete(self, request, *args, **kwargs):
        item = self.get_object()

        delete_aob_item(item=item)

        return success_response(data=None, message="AOB item deleted successfully.")
