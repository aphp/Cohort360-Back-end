import os

from django.apps import AppConfig
from django.conf import settings


class CohortJobServerConfig(AppConfig):
    name = 'cohort_job_server'

    def ready(self):
        settings.COHORT_OPERATORS = [
            {
                "TYPE": "count",
                "OPERATOR_CLASS": "cohort_job_server.cohort_counter.CohortCounter"
            },
            {
                "TYPE": "create",
                "OPERATOR_CLASS": "cohort_job_server.cohort_creator.CohortCreator"
            }
        ]
        env = os.environ
        sjs_username = env.get('SJS_USERNAME', 'SPARK_JOB_SERVER')
        etl_username = env.get('ETL_USERNAME', 'SOLR_ETL')
        settings.api_usernames = [sjs_username, etl_username]
        settings.SJS_URL = env.get('SJS_URL')
        settings.applicative_users = {env.get("SJS_TOKEN"): sjs_username,
                                      env.get("ETL_TOKEN"): etl_username
                                      }
