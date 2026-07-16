from django.conf import settings
from django.db import models

from common.validators import validate_monday


class AOBItem(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    week_start = models.DateField(validators=[validate_monday])
    position = models.PositiveIntegerField()
    # SET_NULL, not CASCADE or PROTECT: deleting the user who created an
    # AOB item must not delete the item itself — AOB history should
    # survive account deletion. PROTECT was rejected because it would
    # instead block deleting the user entirely, which refuses the
    # deletion rather than preserving history through it.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="aob_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-week_start", "position"]
        indexes = [
            models.Index(fields=["-week_start", "position"]),
        ]

    def __str__(self):
        return f"{self.title} — week of {self.week_start}"
