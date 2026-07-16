from django.shortcuts import get_object_or_404

from apps.aob.models import AOBItem


def get_aob_item_by_id(item_id):
    """Fetch a single AOBItem with its creator preloaded in one query (not
    two). Raises Http404 if it doesn't exist.
    """
    queryset = AOBItem.objects.select_related("created_by")
    return get_object_or_404(queryset, pk=item_id)
