import datetime

from django.contrib.auth import get_user_model

from apps.standups.models import Standup
from apps.standups.selectors import list_weekly_standups

User = get_user_model()


def get_weekly_dashboard_data(week_start):
    """Aggregate standup-related dashboard data for the week starting on
    `week_start` (assumed already validated as a Monday) through the
    following Sunday. Only standups are included for now — later this will
    also pull in AOB/PTO/PR/presence data from their own selectors, the
    same way it already reuses apps.standups.selectors here rather than
    re-querying standups itself.
    """
    week_end = week_start + datetime.timedelta(days=6)

    active_users = User.objects.filter(is_active=True).order_by("first_name", "last_name")

    week_standups = Standup.objects.filter(standup_date__range=(week_start, week_end))
    # Kept as a lazy queryset (not a list/set) so the filter()/exclude()
    # below fold it into a subquery instead of a separate round trip.
    submitted_user_ids = week_standups.values_list("user_id", flat=True).distinct()

    return {
        "week_start": week_start,
        "week_end": week_end,
        "total_active_users": active_users.count(),
        "total_submitted_standups": week_standups.count(),
        "users_who_submitted": active_users.filter(id__in=submitted_user_ids),
        "users_who_have_not_submitted": active_users.exclude(id__in=submitted_user_ids),
        "latest_standups": list_weekly_standups(week_start),
    }
