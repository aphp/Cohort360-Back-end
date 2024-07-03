from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


def load_operator(job_type: str):
    for operator_conf in settings.COHORT_OPERATORS:
        try:
            operator_type, cls_path = operator_conf["TYPE"], operator_conf["OPERATOR_CLASS"]
        except KeyError:
            raise ImproperlyConfigured("Missing `TYPE` or `OPERATOR_CLASS` key in operators configuration")
        if operator_type == job_type:
            operator_cls = import_string(cls_path)
            if operator_cls:
                return operator_cls
    raise ImproperlyConfigured(f"No cohort operator of type `{job_type}` is configured")


class CommonService:
    job_type = None

    def __init__(self):
        self.operator = load_operator(job_type=self.job_type)

    def get_special_permissions(self, request):
        return self.operator().get_special_permissions(request)

    def allow_use_full_queryset(self, request) -> bool:
        return request.user.is_authenticated and request.user.username in self.operator().applicative_users
