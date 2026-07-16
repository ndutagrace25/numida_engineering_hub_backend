from django.conf import settings
from django.db import models


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
