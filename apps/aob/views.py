from django_filters.rest_framework import DjangoFilterBackend
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


class AOBItemListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AOBItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AOBItemFilter
    search_fields = ["title", "description", "created_by__first_name", "created_by__last_name"]

    def get_queryset(self):
        return list_aob_items()

    def get(self, request, *args, **kwargs):
        # created_by is a forward, to-one FK (unlike standups' items),
        # so none of these filters/search fields can actually multiply
        # rows — distinct() is kept anyway for consistency and in case a
        # to-many field is ever added to search_fields later.
        queryset = self.filter_queryset(self.get_queryset()).distinct()
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


class AOBItemDetailView(generics.GenericAPIView):
    # IsAOBItemCreator (IsOwnerOrReadOnly with owner_field="created_by")
    # allows safe methods for anyone and restricts unsafe methods to the
    # creator — matching the same reuse already established for standups.
    permission_classes = [IsAuthenticated, IsAOBItemCreator]
    queryset = AOBItem.objects.all()
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
