from django.contrib import admin

from apps.pto.models import PTOEntry


@admin.register(PTOEntry)
class PTOEntryAdmin(admin.ModelAdmin):
    list_display = ["user", "start_date", "end_date", "created_by"]
    list_filter = ["start_date", "end_date"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "reason"]
