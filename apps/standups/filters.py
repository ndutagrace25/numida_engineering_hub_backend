import django_filters

from apps.standups.models import Standup, StandupItem


class StandupFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name="user_id")
    date_after = django_filters.DateFilter(field_name="standup_date", lookup_expr="gte")
    date_before = django_filters.DateFilter(field_name="standup_date", lookup_expr="lte")
    section = django_filters.ChoiceFilter(
        field_name="items__section", choices=StandupItem.Section.choices
    )

    class Meta:
        model = Standup
        fields = ["user", "standup_date", "date_after", "date_before", "section"]
