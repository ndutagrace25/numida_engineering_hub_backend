from django.db import transaction

from apps.pull_requests.models import PullRequestLink


def create_pull_request_link(*, created_by, validated_data):
    """Create a PullRequestLink. created_by is always the authenticated
    user — excluded from validated_data even if present, as a second
    safeguard alongside the serializer's read-only field.
    """
    fields = {key: value for key, value in validated_data.items() if key != "created_by"}

    with transaction.atomic():
        return PullRequestLink.objects.create(created_by=created_by, **fields)


def update_pull_request_link(*, link, validated_data):
    """Update `link`'s editable fields inside one transaction. created_by
    is never touched here — excluded even if present, as a second
    safeguard alongside the serializer's read-only field.
    """
    fields = {key: value for key, value in validated_data.items() if key != "created_by"}

    with transaction.atomic():
        for field, value in fields.items():
            setattr(link, field, value)
        link.save()

    return link


def delete_pull_request_link(*, link):
    with transaction.atomic():
        link.delete()
