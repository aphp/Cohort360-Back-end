from django.db.models import Count

from accesses.accesses_alerts import send_access_expiry_alerts
from accesses.conf_perimeters import perimeters_data_model_objects_update
from accesses.models import Perimeter, Access
from accesses.models.tools import q_is_valid_access, q_role_impacts_lower_levels
from admin_cohort import celery_app
from admin_cohort.settings import ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS, ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS
from admin_cohort.tools.celery_periodic_task_helper import ensure_single_task


@celery_app.task()
@ensure_single_task("check_expiring_accesses")
def check_expiring_accesses():
    send_access_expiry_alerts(days=ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
    send_access_expiry_alerts(days=ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS)


@celery_app.task()
@ensure_single_task("perimeters_daily_update")
def perimeters_daily_update():
    perimeters_data_model_objects_update()


@celery_app.task()
@ensure_single_task("count_users_on_perimeters")
def count_users_on_perimeters():
    count_allowed_users()
    count_allowed_users_in_inferior_levels()
    count_allowed_users_from_above_levels()


def count_allowed_users():
    perimeters_count = Access.objects.filter(q_is_valid_access())\
                                     .distinct("profile__user_id")\
                                     .values("perimeter_id")\
                                     .annotate(count=Count("perimeter_id"))
    for p in perimeters_count:
        try:
            perimeter = Perimeter.objects.get(pk=p.get("perimeter_id"))
            perimeter.count_allowed_users = p.get("count")
            perimeter.save()
        except Perimeter.DoesNotExist:
            continue


def count_allowed_users_in_inferior_levels():
    for perimeter in Perimeter.objects.filter(level=1):
        re_count_allowed_users_inferior_levels(perimeter)


def re_count_allowed_users_inferior_levels(perimeter):
    count = 0
    for child in perimeter.children.all():
        count += child.count_allowed_users
        count += re_count_allowed_users_inferior_levels(perimeter=child)
    perimeter.count_allowed_users_inferior_levels = count
    perimeter.save()
    return count


def count_allowed_users_from_above_levels():
    for perimeter in Perimeter.objects.all():
        parent_perimeters = Perimeter.objects.filter(id__in=perimeter.above_levels)
        count_accesses_impacting_inferior_levels = 0
        for p in parent_perimeters:
            accesses_impacting_inferior_levels = p.accesses.all().filter(q_role_impacts_lower_levels(prefix="Role"))
            count_accesses_impacting_inferior_levels += accesses_impacting_inferior_levels.count()
        perimeter.count_allowed_users_above_levels = count_accesses_impacting_inferior_levels
        perimeter.save()
