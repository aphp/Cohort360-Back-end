from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_cohort.settings')

app = Celery('admin_cohort')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


# @signals.after_setup_logger.connect
# def after_setup_celery_logger(logger, **kwargs):
#     logger.level = INFO
#     formatter = logger.handlers[0].formatter
#     handler = RotatingFileHandler(filename="log/celery.log",
#                                   maxBytes=100 * 1024 * 1024,
#                                   backupCount=1000)
#     handler.setFormatter(formatter)
#     logger.handlers = [handler]
