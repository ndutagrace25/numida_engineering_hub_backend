from django.utils import timezone

from apps.presence.models import UserPresence


def update_user_presence(*, user):
    """Record `user`'s latest activity: creates a UserPresence row if none
    exists yet, or bumps last_seen_at to now if it already does. `user`
    must come from the authenticated request — never from client-supplied
    data such as a user ID in the request body.
    """
    presence, _ = UserPresence.objects.update_or_create(
        user=user,
        defaults={"last_seen_at": timezone.now()},
    )
    return presence


def clear_user_presence(*, user):
    """Delete `user`'s UserPresence row, if any. Presence has no "offline"
    state of its own — get_presence_status() only ever derives ONLINE/
    RECENTLY_ACTIVE/OFFLINE from a last_seen_at timestamp, and a user with
    no presence row at all is already treated as OFFLINE (see
    list_user_presence()) — so removing the row is what makes a just-
    logged-out user stop showing as online immediately, instead of
    lingering until their last heartbeat ages past the ONLINE threshold.
    """
    UserPresence.objects.filter(user=user).delete()
