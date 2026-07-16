from apps.aob.models import AOBItem


def create_aob_item(*, user, validated_data):
    """Create an AOBItem for `user`. created_by is always the authenticated
    user — excluded from validated_data even if present, as a second
    safeguard alongside the serializer's read-only field.
    """
    fields = {key: value for key, value in validated_data.items() if key != "created_by"}
    return AOBItem.objects.create(created_by=user, **fields)
