import django_filters

from apps.aob.models import AOBItem


class AOBItemFilter(django_filters.FilterSet):
    created_by = django_filters.NumberFilter(field_name="created_by_id")
    week_after = django_filters.DateFilter(field_name="week_start", lookup_expr="gte")
    week_before = django_filters.DateFilter(field_name="week_start", lookup_expr="lte")

    class Meta:
        model = AOBItem
        fields = ["week_start", "week_after", "week_before", "created_by"]
