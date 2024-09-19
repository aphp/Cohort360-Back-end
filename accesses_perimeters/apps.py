import os

from django.apps import AppConfig
from django.conf import settings

OMOP_DB_ALIAS = "omop"


class AccessesAuxConfig(AppConfig):
    name = 'accesses_perimeters'

    def ready(self):
        env = os.environ

        settings.OMOP_DB_ALIAS = OMOP_DB_ALIAS
        settings.DATABASES[OMOP_DB_ALIAS] = {'ENGINE': 'django.db.backends.postgresql',
                                             'NAME': env.get("DB_OMOP_NAME"),
                                             'USER': env.get("DB_OMOP_USER"),
                                             'PASSWORD': env.get("DB_OMOP_PASSWORD"),
                                             'HOST': env.get("DB_OMOP_HOST"),
                                             'PORT': env.get("DB_OMOP_PORT"),
                                             'DISABLE_SERVER_SIDE_CURSORS': True,
                                             'ATOMIC_REQUESTS': True,
                                             'TIME_ZONE': None,
                                             'CONN_HEALTH_CHECKS': False,
                                             'CONN_MAX_AGE': 0,
                                             'AUTOCOMMIT': True,
                                             'OPTIONS': {'options': f"-c search_path={env.get('DB_OMOP_SCHEMA')},public"}
                                             }
