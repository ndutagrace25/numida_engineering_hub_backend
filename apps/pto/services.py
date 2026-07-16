from django.db import transaction

from apps.pto.models import PTOEntry


def create_pto_entry(*, created_by, validated_data):
    """Create a PTOEntry. created_by is always the authenticated user —
    excluded from validated_data even if present, as a second safeguard
    alongside the serializer's read-only field. `validated_data["user"]`
    is whoever the PTO is being logged for, which may be a different
    person than created_by.
    """
    fields = {key: value for key, value in validated_data.items() if key != "created_by"}

    with transaction.atomic():
        return PTOEntry.objects.create(created_by=created_by, **fields)


def update_pto_entry(*, entry, validated_data):
    """Update `entry`'s editable fields (user, start_date, end_date,
    reason, handover_url) inside one transaction. created_by is never
    touched here — excluded even if present, as a second safeguard
    alongside the serializer's read-only field.
    """
    fields = {key: value for key, value in validated_data.items() if key != "created_by"}

    with transaction.atomic():
        for field, value in fields.items():
            setattr(entry, field, value)
        entry.save()

    return entry


def delete_pto_entry(*, entry):
    with transaction.atomic():
        entry.delete()
