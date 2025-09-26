from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.signals import setup_logging


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_cohort.settings')

celery_app = Celery('admin_cohort')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

celery_app.autodiscover_tasks()


# Disable Celery’s default logger setup to use Django's logging config
@setup_logging.connect
def setup_celery_logging(**kwargs):
    pass