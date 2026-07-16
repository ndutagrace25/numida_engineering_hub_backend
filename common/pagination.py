"""One reusable pagination class used project-wide for consistent paginated responses."""

from rest_framework.pagination import PageNumberPagination

from common.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from common.responses import paginated_response


class DefaultPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        return paginated_response(
            count=self.page.paginator.count,
            next_url=self.get_next_link(),
            previous_url=self.get_previous_link(),
            results=data,
        )
