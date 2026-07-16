from django.contrib.auth import get_user_model

from apps.presence.models import PresenceStatus, get_presence_status

User = get_user_model()


def list_user_presence():
    """Active users grouped into online/recently_active/offline, derived
    from each user's UserPresence record (if any) via get_presence_status().
    A user without a presence record is treated as offline. Ordered
    alphabetically (first_name, then last_name) within each group.

    select_related() across the reverse one-to-one fetches every active
    user and their presence row (if any) — present or not — in a single
    query, avoiding one query per user.
    """
    users = (
        User.objects.filter(is_active=True)
        .select_related("presence")
        .order_by("first_name", "last_name")
    )

    groups = {
        PresenceStatus.ONLINE: [],
        PresenceStatus.RECENTLY_ACTIVE: [],
        PresenceStatus.OFFLINE: [],
    }

    for user in users:
        presence = getattr(user, "presence", None)
        last_seen_at = presence.last_seen_at if presence else None
        status = get_presence_status(last_seen_at) if presence else PresenceStatus.OFFLINE

        groups[status].append({"user": user, "last_seen_at": last_seen_at})

    return {
        "online": groups[PresenceStatus.ONLINE],
        "recently_active": groups[PresenceStatus.RECENTLY_ACTIVE],
        "offline": groups[PresenceStatus.OFFLINE],
    }
