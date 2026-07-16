from rest_framework import serializers

from apps.accounts.models import User
from apps.presence.models import UserPresence


class PresenceUserSerializer(serializers.ModelSerializer):
    """A deliberately smaller user representation than
    apps.accounts.serializers.UserSerializer — presence data should not
    expose email or account-status fields.
    """

    display_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "display_name"]
        read_only_fields = ["id", "first_name", "last_name"]


class UserPresenceSerializer(serializers.ModelSerializer):
    user = PresenceUserSerializer(read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = UserPresence
        fields = ["user", "last_seen_at", "status"]

    def get_status(self, obj):
        return obj.status
