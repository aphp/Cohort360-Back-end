from accesses.accesses_alerts import send_access_expiry_alerts
from accesses.services.accesses import count_allowed_users, count_allowed_users_in_inferior_levels, \
    count_allowed_users_from_above_levels
from admin_cohort import celery_app
from admin_cohort.settings import ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS, ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS


@celery_app.task()
def check_expiring_accesses():
    send_access_expiry_alerts(days=ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
    send_access_expiry_alerts(days=ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS)


@celery_app.task()
def count_users_on_perimeters():
    count_allowed_users()
    count_allowed_users_in_inferior_levels()
    count_allowed_users_from_above_levels()


