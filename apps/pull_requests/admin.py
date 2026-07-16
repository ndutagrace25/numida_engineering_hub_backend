from django.contrib import admin

from apps.pull_requests.models import PullRequestLink


@admin.register(PullRequestLink)
class PullRequestLinkAdmin(admin.ModelAdmin):
    list_display = ["title", "group_name", "status", "week_start", "position", "created_by"]
    list_filter = ["status", "week_start", "group_name"]
    search_fields = ["title", "group_name", "url"]
