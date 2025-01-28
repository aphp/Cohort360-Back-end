from collections import Counter

from django.conf import settings

from accesses.accesses_alerts import send_access_expiry_alerts
from accesses.models import Perimeter, Access
from accesses.q_expressions import q_impact_inferior_levels
from accesses.services.accesses import accesses_service
from admin_cohort import celery_app


@celery_app.task()
def check_expiring_accesses():
    send_access_expiry_alerts(days=settings.ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
    send_access_expiry_alerts(days=settings.ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS)


@celery_app.task()
def count_users_on_perimeters():
    count_allowed_users()
    count_allowed_users_in_inferior_levels()
    count_allowed_users_from_above_levels()


def count_allowed_users():
    perimeters_ids = Access.objects.filter(accesses_service.q_access_is_valid())\
                                   .distinct("perimeter_id", "profile__user_id")\
                                   .values_list("perimeter_id", flat=True)
    counter = Counter(perimeters_ids)
    for perimeter_id, count in counter.items():
        try:
            perimeter = Perimeter.objects.get(pk=perimeter_id)
            perimeter.count_allowed_users = count
            perimeter.save()
        except Perimeter.DoesNotExist:
            continue


def count_allowed_users_in_inferior_levels():
    for perimeter in Perimeter.objects.filter(level=1):
        re_count_allowed_users_inferior_levels(perimeter)


def re_count_allowed_users_inferior_levels(perimeter):
    user_list = set(Access.objects.filter(accesses_service.q_access_is_valid(), perimeter_id=perimeter.id)
                    .values_list("profile__user_id", flat=True))
    for child in perimeter.children.all():
        user_list.update(re_count_allowed_users_inferior_levels(perimeter=child))
    perimeter.count_allowed_users_inferior_levels = len(user_list)
    perimeter.save()
    return user_list


def count_allowed_users_from_above_levels():
    for perimeter in Perimeter.objects.all():
        parent_perimeters = Perimeter.objects.filter(id__in=perimeter.above_levels)
        count_accesses_impacting_inferior_levels = 0
        for p in parent_perimeters:
            accesses_impacting_inferior_levels = p.accesses.filter(accesses_service.q_access_is_valid(),
                                                                   q_impact_inferior_levels())\
                                                                 .distinct("perimeter_id", "profile__user_id")
            count_accesses_impacting_inferior_levels += accesses_impacting_inferior_levels.count()
        perimeter.count_allowed_users_above_levels = count_accesses_impacting_inferior_levels
        perimeter.save()
