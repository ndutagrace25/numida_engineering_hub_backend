from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
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
from common.schema import (
    AUTHENTICATION_ERROR_RESPONSE,
    not_found_response,
    null_data_envelope,
    permission_error_response,
    success_envelope,
    validation_error_response,
)

_PR_LINK_EXAMPLE = {
    "id": 44,
    "title": "Fix login bug",
    "url": "https://github.com/org/repo/pull/6905",
    "group_name": "App 3.0 PRs",
    "status": "IN_REVIEW",
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
    "CreatePullRequestLinkRequest",
    value={
        "title": "Fix login bug",
        "url": "https://github.com/org/repo/pull/6905",
        "group_name": "App 3.0 PRs",
        "status": "IN_REVIEW",
        "week_start": "2026-07-13",
        "position": 1,
    },
    request_only=True,
)

_PR_LINK_VALIDATION_ERROR_RESPONSE = validation_error_response(
    "url is not HTTPS, week_start does not fall on a Monday, or status is not a valid choice.",
    {"week_start": ["Date must fall on a Monday."]},
)

# Built once and reused across every action that returns this shape
# (create, retrieve, update) — calling success_envelope() again per-action
# would produce distinct dynamic classes that happen to share a name,
# which drf-spectacular flags as a component collision.
_PR_LINK_RESPONSE = success_envelope("PullRequestLinkResponse", PullRequestLinkSerializer())


@extend_schema_view(
    get=extend_schema(
        tags=["Pull Request Links"],
        operation_id="listPullRequestLinks",
        summary="List pull request links",
        description=(
            "List pull request links across all weeks, newest week first. "
            "Supports filtering by week_start, a week_after/week_before "
            "range, status, group_name, and creator, plus free-text search "
            "across title, group name, creator name, and URL."
        ),
        responses={
            200: PullRequestLinkSerializer(many=True),
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
    post=extend_schema(
        tags=["Pull Request Links"],
        operation_id="createPullRequestLink",
        summary="Create a pull request link",
        description="Share a pull request link for a given week.",
        examples=[
            _CREATE_REQUEST_EXAMPLE,
            OpenApiExample(
                "CreatePullRequestLinkResponse",
                value={
                    "message": "Pull request link created successfully.",
                    "data": _PR_LINK_EXAMPLE,
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
        responses={
            201: _PR_LINK_RESPONSE,
            400: _PR_LINK_VALIDATION_ERROR_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
        },
    ),
)
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


@extend_schema_view(
    get=extend_schema(
        tags=["Pull Request Links"],
        operation_id="retrievePullRequestLink",
        summary="Retrieve a pull request link",
        description="Retrieve a single pull request link by id.",
        responses={
            200: _PR_LINK_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
            404: not_found_response("pull request link"),
        },
    ),
    patch=extend_schema(
        tags=["Pull Request Links"],
        operation_id="updatePullRequestLink",
        summary="Update a pull request link",
        description="Partially update a pull request link. Only the creator may update it.",
        examples=[
            OpenApiExample(
                "UpdatePullRequestLinkRequest",
                value={"status": "APPROVED"},
                request_only=True,
            ),
        ],
        responses={
            200: _PR_LINK_RESPONSE,
            400: _PR_LINK_VALIDATION_ERROR_RESPONSE,
            401: AUTHENTICATION_ERROR_RESPONSE,
            403: permission_error_response("You do not have permission to perform this action."),
            404: not_found_response("pull request link"),
        },
    ),
    delete=extend_schema(
        tags=["Pull Request Links"],
        operation_id="deletePullRequestLink",
        summary="Delete a pull request link",
        description="Delete a pull request link. Only the creator may delete it.",
        responses={
            200: null_data_envelope("DeletePullRequestLinkResponse"),
            401: AUTHENTICATION_ERROR_RESPONSE,
            403: permission_error_response("You do not have permission to perform this action."),
            404: not_found_response("pull request link"),
        },
    ),
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
