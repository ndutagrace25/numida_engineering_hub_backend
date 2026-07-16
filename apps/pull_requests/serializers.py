from rest_framework import serializers

from apps.accounts.serializers import MinimalUserSerializer
from apps.pull_requests.models import PullRequestLink
from common.validators import validate_https_url, validate_monday


class PullRequestLinkSerializer(serializers.ModelSerializer):
    created_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = PullRequestLink
        fields = [
            "id",
            "title",
            "url",
            "group_name",
            "status",
            "week_start",
            "position",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_url(self, value):
        validate_https_url(value)
        return value

    def validate_week_start(self, value):
        validate_monday(value)
        return value
