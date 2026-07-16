from django.contrib import admin

from apps.standups.models import Standup, StandupItem


class StandupItemInline(admin.TabularInline):
    model = StandupItem
    extra = 0


@admin.register(Standup)
class StandupAdmin(admin.ModelAdmin):
    list_display = ["user", "standup_date", "created_at"]
    list_filter = ["standup_date"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    inlines = [StandupItemInline]


@admin.register(StandupItem)
class StandupItemAdmin(admin.ModelAdmin):
    list_display = ["standup", "section", "position"]
    list_filter = ["section"]
    search_fields = ["content"]
