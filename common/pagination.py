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

    def get_paginated_response_schema(self, schema):
        # Schema-only override (never called at request time) so
        # drf-spectacular's automatic pagination wrapping reflects the
        # {"message", "data": {...}} envelope get_paginated_response()
        # actually returns, instead of the raw {"count","next",...} shape.
        page_schema = super().get_paginated_response_schema(schema)
        return {
            "type": "object",
            "required": ["message", "data"],
            "properties": {
                "message": {"type": "string", "example": "Request completed successfully."},
                "data": page_schema,
            },
        }
