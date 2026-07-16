import datetime

from django.contrib.auth import get_user_model

from apps.aob.selectors import list_aob_items_for_week
from apps.presence.selectors import list_user_presence
from apps.pto.selectors import list_pto_entries_for_week
from apps.pull_requests.selectors import list_pull_request_links_for_week
from apps.standups.models import Standup
from apps.standups.selectors import list_weekly_standups

User = get_user_model()


def _get_standup_summary(week_start, week_end):
    """Active-user standup submission totals for the week — this logic
    isn't owned by any single module, so it lives in the dashboard itself
    rather than being force-fit into apps.standups.
    """
    active_users = User.objects.filter(is_active=True).order_by("first_name", "last_name")

    week_standups = Standup.objects.filter(standup_date__range=(week_start, week_end))
    # Kept as a lazy queryset (not a list/set) so the filter()/exclude()
    # below fold it into a subquery instead of a separate round trip.
    submitted_user_ids = week_standups.values_list("user_id", flat=True).distinct()

    return {
        "total_active_users": active_users.count(),
        "total_submitted_standups": week_standups.count(),
        "users_who_submitted": active_users.filter(id__in=submitted_user_ids),
        "users_who_have_not_submitted": active_users.exclude(id__in=submitted_user_ids),
    }


def get_weekly_dashboard_data(week_start):
    """Aggregate dashboard data for the week starting on `week_start`
    (assumed already validated as a Monday) through the following Sunday.

    Each module owns its own week-scoped query logic — this function only
    calls into apps.standups/aob/pto/pull_requests/presence selectors and
    assembles their results, rather than re-querying any of them itself.
    Presence is intentionally NOT scoped to the week: it always reflects
    current state, per the module's own semantics.
    """
    week_end = week_start + datetime.timedelta(days=6)

    return {
        "week_start": week_start,
        "week_end": week_end,
        "standup_summary": _get_standup_summary(week_start, week_end),
        "weekly_standups": list_weekly_standups(week_start),
        "presence": list_user_presence(),
        "aob_items": list_aob_items_for_week(week_start),
        "pto_entries": list_pto_entries_for_week(week_start, week_end),
        "pull_request_links": list_pull_request_links_for_week(week_start),
    }
