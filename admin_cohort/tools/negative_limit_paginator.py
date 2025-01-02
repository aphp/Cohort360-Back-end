from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination



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
                    return settings.PAGINATION_MAX_LIMIT
        return super().get_limit(request)
