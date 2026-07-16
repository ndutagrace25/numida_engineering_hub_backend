"""Reusable base permissions. Feature apps compose or subclass these; no
app-specific rules live here.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """Allows safe methods to anyone; write methods only to the object's owner."""

    owner_field = "owner"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return getattr(obj, self.owner_field, None) == request.user


class IsCreatorOrReadOnly(BasePermission):
    """Allows safe methods to anyone; write methods only to the object's creator."""

    creator_field = "created_by"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return getattr(obj, self.creator_field, None) == request.user
