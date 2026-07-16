from django_filters.rest_framework import DjangoFilterBackend
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
        # filters/search fields can multiply rows — distinct() is kept
        # anyway for consistency with the other list endpoints.
        queryset = self.filter_queryset(self.get_queryset()).distinct()
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


class PTOEntryDetailView(generics.GenericAPIView):
    # IsPTOEntryCreator (IsOwnerOrReadOnly with owner_field="created_by")
    # allows safe methods for anyone and restricts unsafe methods to the
    # creator — matching the same reuse already established for standups
    # and AOB items.
    permission_classes = [IsAuthenticated, IsPTOEntryCreator]
    queryset = PTOEntry.objects.all()
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
