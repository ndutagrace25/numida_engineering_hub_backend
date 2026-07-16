from common.permissions import IsOwnerOrReadOnly


class IsAOBItemCreator(IsOwnerOrReadOnly):
    owner_field = "created_by"
