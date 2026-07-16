import django_filters

from apps.pto.models import PTOEntry


class PTOEntryFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name="user_id")
    created_by = django_filters.NumberFilter(field_name="created_by_id")
    date_after = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    date_before = django_filters.DateFilter(field_name="start_date", lookup_expr="lte")
    active_on = django_filters.DateFilter(method="filter_active_on")

    class Meta:
        model = PTOEntry
        fields = [
            "user",
            "created_by",
            "start_date",
            "end_date",
            "date_after",
            "date_before",
            "active_on",
        ]

    def filter_active_on(self, queryset, name, value):
        return queryset.filter(start_date__lte=value, end_date__gte=value)
