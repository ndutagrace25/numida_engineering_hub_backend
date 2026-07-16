import datetime

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from apps.standups.models import Standup, StandupItem

_ITEMS_PREFETCH = Prefetch("items", queryset=StandupItem.objects.order_by("section", "position"))


def get_standup_by_id(standup_id):
    """Fetch a single Standup with its user and ordered items preloaded in
    two queries total (not N+1). Raises Http404 if it doesn't exist.
    """
    queryset = Standup.objects.select_related("user").prefetch_related(_ITEMS_PREFETCH)
    return get_object_or_404(queryset, pk=standup_id)


def list_standups():
    """All standups, newest standup_date first (then newest created_at as a
    tiebreaker), with user and ordered items preloaded — two queries total
    regardless of how many standups are returned.
    """
    return (
        Standup.objects.select_related("user")
        .prefetch_related(_ITEMS_PREFETCH)
        .order_by("-standup_date", "-created_at")
    )


def list_user_standups(user):
    """Same ordering/preloading as list_standups(), scoped to `user`'s own
    standups only.
    """
    return (
        Standup.objects.filter(user=user)
        .select_related("user")
        .prefetch_related(_ITEMS_PREFETCH)
        .order_by("-standup_date", "-created_at")
    )


def list_weekly_standups(week_start):
    """All standups (any user) from `week_start` through the following
    Sunday, ordered by standup_date then the owner's name. `week_start` is
    assumed to already be validated as a Monday — this function doesn't
    check that itself.
    """
    week_end = week_start + datetime.timedelta(days=6)
    return (
        Standup.objects.filter(standup_date__gte=week_start, standup_date__lte=week_end)
        .select_related("user")
        .prefetch_related(_ITEMS_PREFETCH)
        .order_by("standup_date", "user__first_name", "user__last_name")
    )
