from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.standups.models import Standup, StandupItem
from common.validators import validate_monday

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


class StandupSerializer(serializers.ModelSerializer):
    """Validation and representation only — creating/updating a Standup and
    its nested items is deliberately handled by apps.standups.services
    (create_standup()/update_standup()), not by overriding create()/
    update() here, to keep write logic in the service layer.
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
        extra_kwargs = {
            "blockers": {
                "help_text": "Free-text description of anything blocking progress. Optional."
            },
        }

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
        # Under partial=True, an absent "items" key means "leave items
        # alone" (e.g. a PATCH that only touches blockers) — not "replace
        # with zero items" — so the required-sections check only applies
        # when items are actually part of this update.
        if self.partial and "items" not in attrs:
            return attrs

        items = attrs.get("items", [])
        sections_present = {item["section"] for item in items}
        missing = [section for section in REQUIRED_SECTIONS if section not in sections_present]
        if missing:
            raise serializers.ValidationError(
                {"items": f"At least one item is required for: {', '.join(missing)}."}
            )
        return attrs


class WeeklyStandupsQuerySerializer(serializers.Serializer):
    """Validates the `week_start` query parameter for the weekly standups
    endpoint. Not tied to any model — pure input validation.
    """

    week_start = serializers.DateField(
        help_text="The Monday that starts the target week, as YYYY-MM-DD."
    )

    def validate_week_start(self, value):
        validate_monday(value)
        return value
