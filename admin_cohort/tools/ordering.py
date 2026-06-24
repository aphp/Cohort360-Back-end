from django.core.validators import EMPTY_VALUES
from django.db.models import F
from django_filters import OrderingFilter


class NullsLastOrderingFilter(OrderingFilter):
    # Postgres orders NULLs first on a descending sort by default.

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        ordering = []
        for param in value:
            if param in EMPTY_VALUES:
                continue
            field_name = self.get_ordering_value(param)
            descending = field_name.startswith("-")
            expression = F(field_name[1:] if descending else field_name)
            ordering.append(expression.desc(nulls_last=True) if descending else expression.asc(nulls_last=True))
        return qs.order_by(*ordering)
