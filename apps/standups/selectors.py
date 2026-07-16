from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from apps.standups.models import Standup, StandupItem


def get_standup_by_id(standup_id):
    """Fetch a single Standup with its user and ordered items preloaded in
    two queries total (not N+1). Raises Http404 if it doesn't exist.
    """
    queryset = Standup.objects.select_related("user").prefetch_related(
        Prefetch("items", queryset=StandupItem.objects.order_by("section", "position"))
    )
    return get_object_or_404(queryset, pk=standup_id)
