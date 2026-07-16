from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import MinimalUserSerializer
from apps.presence.models import PresenceStatus, UserPresence


class UserPresenceSerializer(serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = UserPresence
        fields = ["user", "last_seen_at", "status"]

    @extend_schema_field(serializers.ChoiceField(choices=PresenceStatus.choices))
    def get_status(self, obj) -> str:
        return obj.status


class UserPresenceEntrySerializer(serializers.Serializer):
    """One row of the grouped presence list — status itself isn't repeated
    here since it's already conveyed by which group (online/
    recently_active/offline) the entry appears under.
    """

    user = MinimalUserSerializer(read_only=True)
    last_seen_at = serializers.DateTimeField(read_only=True, allow_null=True)


class UserPresenceListSerializer(serializers.Serializer):
    online = UserPresenceEntrySerializer(many=True, read_only=True)
    recently_active = UserPresenceEntrySerializer(many=True, read_only=True)
    offline = UserPresenceEntrySerializer(many=True, read_only=True)
