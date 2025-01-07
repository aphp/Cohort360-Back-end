import os

from django.apps import AppConfig
from django.conf import settings


env = os.environ


class CohortJobServerConfig(AppConfig):
    name = 'cohort_job_server'

    USE_SOLR = getattr(settings, 'USE_SOLR', env.get("USE_SOLR", False))

    COHORT_OPERATORS = [
        {
            "TYPE": "count",
            "OPERATOR_CLASS": "cohort_job_server.cohort_counter.CohortCounter"
        },
        {
            "TYPE": "create",
            "OPERATOR_CLASS": "cohort_job_server.cohort_creator.CohortCreator"
        }
    ]

    sjs_username = env.get('SJS_USERNAME', 'SPARK_JOB_SERVER')
    etl_username = env.get('ETL_USERNAME', 'SOLR_ETL')
    APPLICATIVE_USERS = [sjs_username, etl_username]
    APPLICATIVE_USERS_TOKENS = {env.get("SJS_TOKEN"): sjs_username,
                                env.get("ETL_TOKEN"): etl_username
                                }
