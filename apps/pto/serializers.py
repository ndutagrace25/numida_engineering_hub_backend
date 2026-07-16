from rest_framework import serializers

from apps.accounts.serializers import MinimalUserSerializer
from apps.pto.models import PTOEntry
from common.validators import validate_https_url


class PTOEntrySerializer(serializers.ModelSerializer):
    """`user` (the person taking PTO) is writable as a plain user id — a
    creator can log PTO for someone else — but always read back as the
    limited nested representation, via to_representation() below.
    created_by is always the authenticated user and never writable.
    """

    created_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = PTOEntry
        fields = [
            "id",
            "user",
            "start_date",
            "end_date",
            "reason",
            "handover_url",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "user": {
                "help_text": (
                    "Id of the user taking PTO — may differ from the authenticated creator."
                )
            },
            "handover_url": {"help_text": "Optional HTTPS link to handover notes."},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["user"] = MinimalUserSerializer(instance.user).data if instance.user else None
        return data

    def validate_handover_url(self, value):
        if value:
            validate_https_url(value)
        return value

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )
        return attrs
