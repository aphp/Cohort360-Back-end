from rest_framework.pagination import LimitOffsetPagination

from admin_cohort.settings import PAGINATION_MAX_LIMIT


class NegativeLimitOffsetPagination(LimitOffsetPagination):

    def get_limit(self, request):
        if self.limit_query_param:
            limit = request.query_params.get(self.limit_query_param)
            if limit is not None:
                try:
                    limit = int(limit)
                except ValueError:
                    return self.default_limit
                if limit < 0:
                    return PAGINATION_MAX_LIMIT
        return super().get_limit(request)
