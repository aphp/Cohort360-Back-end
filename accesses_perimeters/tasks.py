from accesses_perimeters.perimeters_updater import perimeters_data_model_objects_update
from admin_cohort import celery_app
from admin_cohort.tools.celery_periodic_task_helper import ensure_single_task


@celery_app.task()
@ensure_single_task("perimeters_daily_update")
def perimeters_daily_update():
    perimeters_data_model_objects_update()
