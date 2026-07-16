from django.db import transaction

from apps.aob.models import AOBItem


def create_aob_item(*, created_by, validated_data):
    """Create an AOBItem. created_by is always the authenticated user —
    excluded from validated_data even if present, as a second safeguard
    alongside the serializer's read-only field.
    """
    fields = {key: value for key, value in validated_data.items() if key != "created_by"}
    return AOBItem.objects.create(created_by=created_by, **fields)


def update_aob_item(*, item, validated_data):
    """Update `item`'s editable fields (title, description, external_url,
    week_start, position) inside one transaction. created_by is never
    touched here — excluded even if present, as a second safeguard
    alongside the serializer's read-only field.
    """
    fields = {key: value for key, value in validated_data.items() if key != "created_by"}

    with transaction.atomic():
        for field, value in fields.items():
            setattr(item, field, value)
        item.save()

    return item


def delete_aob_item(*, item):
    with transaction.atomic():
        item.delete()
