from typing import Union

from django.utils import timezone

from admin_cohort.models import MaintenancePhase


def get_next_maintenance() -> Union[MaintenancePhase, None]:
    now = timezone.now()
    current = MaintenancePhase.objects.filter(start_datetime__lte=now, end_datetime__gte=now)\
                                      .order_by('-end_datetime')\
                                      .first()
    if current:
        return current
    next_maintenance = MaintenancePhase.objects.filter(start_datetime__gte=now)\
                                               .order_by('start_datetime')\
                                               .first()
    return next_maintenance
