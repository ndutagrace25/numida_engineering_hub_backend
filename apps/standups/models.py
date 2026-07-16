from django.conf import settings
from django.db import models


class Standup(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="standups",
    )
    standup_date = models.DateField()
    blockers = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-standup_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "standup_date"], name="unique_standup_per_user_per_date"
            ),
        ]
        indexes = [
            models.Index(fields=["standup_date"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.standup_date}"


class StandupItem(models.Model):
    class Section(models.TextChoices):
        COMPLETED = "COMPLETED", "What did I do?"
        CURRENT = "CURRENT", "What am I working on?"
        PLANNED = "PLANNED", "What do I plan to do?"
        MEETING = "MEETING", "Meetings"

    standup = models.ForeignKey(Standup, on_delete=models.CASCADE, related_name="items")
    section = models.CharField(max_length=20, choices=Section.choices)
    content = models.TextField()
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["section", "position"]
        indexes = [
            models.Index(fields=["standup", "section", "position"]),
        ]

    def __str__(self):
        return f"{self.standup} — {self.get_section_display()} #{self.position}"
