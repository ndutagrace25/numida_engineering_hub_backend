from django.conf import settings
from django.db import models

from common.validators import validate_https_url, validate_monday


class PullRequestLink(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_REVIEW = "IN_REVIEW", "In review"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes requested"
        APPROVED = "APPROVED", "Approved"
        BLOCKED = "BLOCKED", "Blocked"

    title = models.CharField(max_length=255)
    # HTTPS-only, but otherwise unrestricted — this accepts both GitHub PR
    # URLs and approved internal links, since neither needs a stricter
    # domain check than "must be HTTPS".
    url = models.URLField(validators=[validate_https_url])
    group_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices)
    week_start = models.DateField(validators=[validate_monday])
    position = models.PositiveIntegerField()
    # SET_NULL, not CASCADE or PROTECT: deleting the user who created a PR
    # link must not delete the link itself — PR-link history should
    # survive account deletion, the same reasoning already used for
    # AOBItem.created_by and PTOEntry.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pull_request_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-week_start", "group_name", "position", "-created_at"]
        indexes = [
            # Matches the default ordering's leading columns.
            models.Index(fields=["-week_start", "group_name", "position"]),
            # status isn't part of the ordering, so it needs its own index
            # to serve "filter by status" queries efficiently.
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()}) — week of {self.week_start}"
