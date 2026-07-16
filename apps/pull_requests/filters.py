import django_filters

from apps.pull_requests.models import PullRequestLink


class PullRequestLinkFilter(django_filters.FilterSet):
    created_by = django_filters.NumberFilter(field_name="created_by_id")
    week_after = django_filters.DateFilter(field_name="week_start", lookup_expr="gte")
    week_before = django_filters.DateFilter(field_name="week_start", lookup_expr="lte")

    class Meta:
        model = PullRequestLink
        fields = [
            "week_start",
            "week_after",
            "week_before",
            "status",
            "group_name",
            "created_by",
        ]
