from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.standups.models import Standup, StandupItem
from common.validators import validate_non_empty_string

REQUIRED_SECTIONS = (
    StandupItem.Section.COMPLETED,
    StandupItem.Section.CURRENT,
    StandupItem.Section.PLANNED,
)


class StandupItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandupItem
        fields = ["id", "section", "content", "position", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_content(self, value):
        validate_non_empty_string(value)
        return value


class StandupSerializer(serializers.ModelSerializer):
    """Validation-only for now — create()/update() for the nested items list
    are intentionally not implemented yet.
    """

    user = UserSerializer(read_only=True)
    items = StandupItemSerializer(many=True)

    class Meta:
        model = Standup
        fields = [
            "id",
            "user",
            "standup_date",
            "blockers",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_items(self, items):
        seen_positions = set()
        for item in items:
            key = (item["section"], item["position"])
            if key in seen_positions:
                raise serializers.ValidationError(
                    f"Duplicate position {item['position']} within section {item['section']}."
                )
            seen_positions.add(key)
        return items

    def validate(self, attrs):
        items = attrs.get("items", [])
        sections_present = {item["section"] for item in items}
        missing = [section for section in REQUIRED_SECTIONS if section not in sections_present]
        if missing:
            raise serializers.ValidationError(
                {"items": f"At least one item is required for: {', '.join(missing)}."}
            )
        return attrs
