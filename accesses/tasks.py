from itertools import chain

from celery import shared_task

from accesses.accesses_alerts import send_access_expiry_alerts
from accesses.conf_perimeters import perimeters_data_model_objects_update
from accesses.models import Perimeter
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


@shared_task
def add_new_allowed_user(perimeter_id: int, user_id: int):
    try:
        perimeter = Perimeter.objects.get(id=perimeter_id)
    except Perimeter.DoesNotExist:
        return
    perimeter.allowed_users = list(set((perimeter.allowed_users or []) + [user_id]))
    perimeter.save()
    add_user_to_parent_perimeters(perimeter=perimeter, user_id=user_id)
    add_user_to_child_perimeters(perimeter=perimeter, user_id=user_id)


@shared_task
def revoke_user(perimeter_id: int, user_id: int):
    try:
        perimeter = Perimeter.objects.get(id=perimeter_id)
        perimeter.allowed_users.remove(user_id)
        perimeter.save()
    except (Perimeter.DoesNotExist, ValueError):
        return
    revoke_user_from_parent_perimeters(perimeter=perimeter, user_id=user_id)
    revoke_user_from_child_perimeters(perimeter=perimeter, user_id=user_id)


def add_user_to_parent_perimeters(perimeter: Perimeter, user_id: int):
    parent = perimeter.parent
    if parent:
        allowed_users_inferior_levels = parent.allowed_users_inferior_levels or []
        parent.allowed_users_inferior_levels = list(set(allowed_users_inferior_levels + [user_id]))
        parent.save()
        if parent.parent:
            add_user_to_parent_perimeters(perimeter=parent, user_id=user_id)


def add_user_to_child_perimeters(perimeter: Perimeter, user_id: int):
    for child in perimeter.children.all():
        allowed_users_above_levels = child.allowed_users_above_levels or []
        child.allowed_users_above_levels = list(set(allowed_users_above_levels + [user_id]))
        child.save()
        if child.children.all():
            add_user_to_child_perimeters(perimeter=child, user_id=user_id)


def revoke_user_from_parent_perimeters(perimeter: Perimeter, user_id: int):
    parent = perimeter.parent
    for child in parent.children.all():
        if user_id in chain(child.allowed_users,
                            child.allowed_users_inferior_levels):
            return
    try:
        parent.allowed_users_inferior_levels.remove(user_id)
        parent.save()
    except ValueError:
        pass
    if parent.parent:
        revoke_user_from_parent_perimeters(perimeter=parent, user_id=user_id)


def revoke_user_from_child_perimeters(perimeter: Perimeter, user_id: int):
    if user_id not in chain(perimeter.allowed_users,
                            perimeter.allowed_users_above_levels):
        for child in perimeter.children.all():
            try:
                child.allowed_users_above_levels.remove(user_id)
                child.save()
            except ValueError:
                pass
            if child.children.all():
                revoke_user_from_child_perimeters(perimeter=child, user_id=user_id)
