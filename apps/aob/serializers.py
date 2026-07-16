from rest_framework import serializers

from apps.accounts.serializers import MinimalUserSerializer
from apps.aob.models import AOBItem
from common.validators import validate_https_url, validate_monday, validate_non_empty_string


class AOBItemSerializer(serializers.ModelSerializer):
    created_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = AOBItem
        fields = [
            "id",
            "title",
            "description",
            "external_url",
            "week_start",
            "position",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value):
        validate_non_empty_string(value)
        return value

    def validate_external_url(self, value):
        if value:
            validate_https_url(value)
        return value

    def validate_week_start(self, value):
        validate_monday(value)
        return value
