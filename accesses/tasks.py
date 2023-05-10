from accesses.accesses_alerts import send_access_expiry_alerts
from accesses.conf_perimeters import perimeters_data_model_objects_update
from admin_cohort import celery_app
from admin_cohort.settings import ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS, ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS


@celery_app.task()
def check_expiring_accesses():
    send_access_expiry_alerts(days=ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
    send_access_expiry_alerts(days=ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS)


@celery_app.task()
def perimeters_daily_update():
    perimeters_data_model_objects_update()
