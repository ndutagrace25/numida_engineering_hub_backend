from common.permissions import IsOwnerOrReadOnly


class IsPTOEntryCreator(IsOwnerOrReadOnly):
    owner_field = "created_by"
