from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class PTOEntry(models.Model):
    # SET_NULL (not CASCADE or PROTECT) for both user and created_by: PTO
    # records are historical/compliance data that should survive account
    # deletion, whether it's the person who took the leave or the person
    # who logged the record on their behalf. PROTECT was rejected because
    # it would block deleting the user entirely rather than preserving
    # history through it — the same reasoning as AOBItem.created_by.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pto_entries",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    handover_url = models.URLField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pto_entries_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "user__first_name", "user__last_name"]
        indexes = [
            # user already gets an index automatically as a ForeignKey.
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.start_date} to {self.end_date}"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": _("End date cannot be earlier than start date.")})
