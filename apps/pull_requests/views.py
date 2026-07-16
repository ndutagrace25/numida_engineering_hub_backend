from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.pull_requests.filters import PullRequestLinkFilter
from apps.pull_requests.models import PullRequestLink
from apps.pull_requests.permissions import IsPullRequestLinkCreator
from apps.pull_requests.selectors import get_pull_request_link_by_id, list_pull_request_links
from apps.pull_requests.serializers import PullRequestLinkSerializer
from apps.pull_requests.services import (
    create_pull_request_link,
    delete_pull_request_link,
    update_pull_request_link,
)
from common.responses import created_response, success_response


class PullRequestLinkListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PullRequestLinkSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = PullRequestLinkFilter
    search_fields = [
        "title",
        "group_name",
        "created_by__first_name",
        "created_by__last_name",
        "url",
    ]

    def get_queryset(self):
        return list_pull_request_links()

    def get(self, request, *args, **kwargs):
        # created_by is a forward, to-one FK, so none of these
        # filters/search fields can multiply rows — distinct() is kept
        # anyway for consistency with the other list endpoints.
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = PullRequestLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        link = create_pull_request_link(
            created_by=request.user, validated_data=serializer.validated_data
        )

        return created_response(
            data=PullRequestLinkSerializer(link).data,
            message="Pull request link created successfully.",
        )


class PullRequestLinkDetailView(generics.GenericAPIView):
    # IsPullRequestLinkCreator (IsOwnerOrReadOnly with
    # owner_field="created_by") allows safe methods for anyone and
    # restricts unsafe methods to the creator — matching the same reuse
    # already established for standups, AOB items, and PTO entries.
    permission_classes = [IsAuthenticated, IsPullRequestLinkCreator]
    queryset = PullRequestLink.objects.all()
    serializer_class = PullRequestLinkSerializer

    def get(self, request, *args, **kwargs):
        # Bypasses get_object()'s plain queryset in favor of the selector's
        # select_related-optimized one, but still runs the same
        # object-level permission check get_object() would have (a no-op
        # here, since GET is a safe method IsOwnerOrReadOnly allows anyone).
        link = get_pull_request_link_by_id(kwargs["pk"])
        self.check_object_permissions(request, link)

        return success_response(
            data=PullRequestLinkSerializer(link).data,
            message="Pull request link retrieved successfully.",
        )

    def patch(self, request, *args, **kwargs):
        # get_object() 404s for a nonexistent pk and, via
        # check_object_permissions(), 403s for a pk that exists but wasn't
        # created by request.user.
        link = self.get_object()

        serializer = self.get_serializer(link, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = update_pull_request_link(link=link, validated_data=serializer.validated_data)

        return success_response(
            data=PullRequestLinkSerializer(updated).data,
            message="Pull request link updated successfully.",
        )

    def delete(self, request, *args, **kwargs):
        link = self.get_object()

        delete_pull_request_link(link=link)

        return success_response(data=None, message="Pull request link deleted successfully.")
