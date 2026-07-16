from common.permissions import IsOwnerOrReadOnly


class IsPullRequestLinkCreator(IsOwnerOrReadOnly):
    owner_field = "created_by"
