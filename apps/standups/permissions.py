from common.permissions import IsOwnerOrReadOnly


class IsStandupOwner(IsOwnerOrReadOnly):
    owner_field = "user"
