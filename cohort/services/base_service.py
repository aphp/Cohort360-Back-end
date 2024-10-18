from typing import Optional

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from cohort.apps import CohortConfig


def load_operator(cls_path: str):
    try:
        operator_cls = import_string(cls_path)
        return operator_cls()
    except ImportError as ie:
        raise ImproperlyConfigured(f"No cohort operator defined at `{cls_path}`") from ie


def load_operator_cls(job_type: str) -> Optional[str]:
    for operator_conf in CohortConfig.COHORT_OPERATORS:
        try:
            operator_type, cls_path = operator_conf["TYPE"], operator_conf["OPERATOR_CLASS"]
        except KeyError:
            raise ImproperlyConfigured("Missing `TYPE` or `OPERATOR_CLASS` key in operators configuration")
        if operator_type == job_type:
            return cls_path
    raise ImproperlyConfigured(f"No cohort operator of type `{job_type}` is configured")


class CommonService:
    job_type = None

    def __init__(self):
        self.operator_cls = load_operator_cls(job_type=self.job_type)
        self.operator = load_operator(cls_path=self.operator_cls)

    def get_special_permissions(self, request):
        return self.operator.get_special_permissions(request)

    def allow_use_full_queryset(self, request) -> bool:
        return request.user.is_authenticated and request.user.username in self.operator.applicative_users
