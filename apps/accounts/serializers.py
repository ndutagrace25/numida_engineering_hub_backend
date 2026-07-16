from django.contrib.auth import authenticate
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


class LoginSerializer(serializers.Serializer):
    """Validates login credentials and authenticates the user. Does not
    touch the session — that is the view's responsibility.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )

        # Same generic message whether the email is unknown, the password is
        # wrong, or the account is inactive — so login can't be used to probe
        # which accounts exist.
        if user is None:
            raise serializers.ValidationError(
                "Unable to log in with the provided credentials.",
                code="invalid_credentials",
            )

        attrs["user"] = user
        return attrs
