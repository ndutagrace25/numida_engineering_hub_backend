from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Output-only representation of a user. Every field is read-only —
    this serializer does not support creating users or updating passwords;
    that will be added by dedicated serializers later.
    """

    display_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
        ]


class CurrentUserSerializer(UserSerializer):
    """Used by the future `/auth/me/` endpoint. Identical to UserSerializer
    today; kept as its own class so that endpoint can diverge later without
    changing the general-purpose UserSerializer.
    """
