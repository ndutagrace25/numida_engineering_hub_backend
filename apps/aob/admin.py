from django.contrib import admin

from apps.aob.models import AOBItem


@admin.register(AOBItem)
class AOBItemAdmin(admin.ModelAdmin):
    list_display = ["title", "week_start", "position", "created_by"]
    list_filter = ["week_start"]
    search_fields = ["title", "description"]
