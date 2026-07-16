import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

ONLINE_THRESHOLD = datetime.timedelta(minutes=2)
RECENTLY_ACTIVE_THRESHOLD = datetime.timedelta(minutes=15)


class PresenceStatus(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    RECENTLY_ACTIVE = "RECENTLY_ACTIVE", "Recently active"
    OFFLINE = "OFFLINE", "Offline"


def get_presence_status(last_seen_at):
    """Derive a PresenceStatus from a last_seen_at timestamp. Never stored —
    always computed fresh against the current time, so it's reusable from
    selectors and future endpoints without going stale.
    """
    elapsed = timezone.now() - last_seen_at
    if elapsed <= ONLINE_THRESHOLD:
        return PresenceStatus.ONLINE
    if elapsed <= RECENTLY_ACTIVE_THRESHOLD:
        return PresenceStatus.RECENTLY_ACTIVE
    return PresenceStatus.OFFLINE


class UserPresence(models.Model):
    # OneToOneField already enforces "at most one presence record per
    # user" via its implicit unique constraint — no separate constraint
    # needed.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presence",
    )
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["last_seen_at"]),
        ]

    def __str__(self):
        return f"{self.user} — last seen {self.last_seen_at}"

    @property
    def status(self):
        return get_presence_status(self.last_seen_at)
