from django.contrib import admin

from apps.presence.models import UserPresence


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ["user", "last_seen_at"]
    list_filter = ["last_seen_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
