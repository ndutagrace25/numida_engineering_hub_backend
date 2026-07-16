from django.db import transaction

from apps.standups.models import Standup, StandupItem


def create_standup(*, user, validated_data):
    """Create a Standup and its nested StandupItems for `user`.

    `validated_data` is expected to already be validated (e.g. via
    StandupSerializer) — this only assigns ownership and persists.
    Duplicate (user, standup_date) pairs surface as IntegrityError from
    the model's UniqueConstraint; this function doesn't pre-check that
    itself.
    """
    items_data = validated_data["items"]
    standup_fields = {key: value for key, value in validated_data.items() if key != "items"}

    with transaction.atomic():
        standup = Standup.objects.create(user=user, **standup_fields)
        StandupItem.objects.bulk_create(StandupItem(standup=standup, **item) for item in items_data)

    return standup
