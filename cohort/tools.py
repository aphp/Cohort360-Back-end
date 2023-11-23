

def log_delete_task(cr_uuid, msg):
    _celery_logger.info(f"Cohort Delete Task [CR: {cr_uuid}] {msg}")
