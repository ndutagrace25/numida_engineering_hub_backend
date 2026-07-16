from django.shortcuts import get_object_or_404

from apps.pull_requests.models import PullRequestLink


def get_pull_request_link_by_id(link_id):
    """Fetch a single PullRequestLink with its creator preloaded in one
    query (not two). Raises Http404 if it doesn't exist.
    """
    queryset = PullRequestLink.objects.select_related("created_by")
    return get_object_or_404(queryset, pk=link_id)


def list_pull_request_links():
    """All PR links, ordered by week_start descending, group_name
    ascending, position ascending, created_at descending, with the
    creator preloaded — one query regardless of how many links are
    returned.
    """
    return PullRequestLink.objects.select_related("created_by").order_by(
        "-week_start", "group_name", "position", "-created_at"
    )


def list_pull_request_links_for_week(week_start):
    """PR links for a single week — reuses list_pull_request_links() for
    the select_related/ordering and just adds the week_start filter, so
    callers like the dashboard don't duplicate that query logic.
    """
    return list_pull_request_links().filter(week_start=week_start)
