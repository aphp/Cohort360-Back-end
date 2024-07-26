from accesses_perimeters.perimeters_updater import perimeters_data_model_objects_update
from admin_cohort import celery_app


@celery_app.task()
def perimeters_daily_update():
    perimeters_data_model_objects_update()
