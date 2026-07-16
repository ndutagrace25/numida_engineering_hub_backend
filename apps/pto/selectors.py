from django.shortcuts import get_object_or_404

from apps.pto.models import PTOEntry


def get_pto_entry_by_id(entry_id):
    """Fetch a single PTOEntry with its user and creator preloaded in one
    query (not two). Raises Http404 if it doesn't exist.
    """
    queryset = PTOEntry.objects.select_related("user", "created_by")
    return get_object_or_404(queryset, pk=entry_id)


def list_pto_entries():
    """All PTO entries, ordered by start_date then end_date then the
    PTO-taker's first/last name, with user and creator preloaded — one
    query regardless of how many entries are returned.
    """
    return PTOEntry.objects.select_related("user", "created_by").order_by(
        "start_date", "end_date", "user__first_name", "user__last_name"
    )
