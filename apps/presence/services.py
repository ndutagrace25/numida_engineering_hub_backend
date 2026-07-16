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
