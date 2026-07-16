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


def update_standup(*, standup, validated_data):
    """Update `standup` and fully replace its nested StandupItems.

    `validated_data` is expected to already be validated (e.g. via
    StandupSerializer, including under partial=True). The owner is never
    touched here — "user" is excluded even if present, as a second
    safeguard alongside the serializer's read-only field — and a duplicate
    (user, standup_date) conflict with a *different* standup surfaces as
    IntegrityError from the model's UniqueConstraint, same as
    create_standup(). If "items" is absent (a partial update that doesn't
    touch items at all), existing items are left untouched rather than
    being wiped out.
    """
    items_data = validated_data.get("items")
    standup_fields = {
        key: value for key, value in validated_data.items() if key not in ("items", "user")
    }

    with transaction.atomic():
        for field, value in standup_fields.items():
            setattr(standup, field, value)
        standup.save()

        if items_data is not None:
            standup.items.all().delete()
            StandupItem.objects.bulk_create(
                StandupItem(standup=standup, **item) for item in items_data
            )

    return standup


def delete_standup(*, standup):
    """Delete `standup`. StandupItems cascade-delete via their FK's
    on_delete=CASCADE — nothing extra to do for them here.
    """
    with transaction.atomic():
        standup.delete()
