import os

from django.apps import AppConfig

env = os.environ


class CohortJobServerConfig(AppConfig):
    name = 'cohort_job_server'

    USE_SOLR = env.get('USE_SOLR', False)
    TEST_FHIR_QUERIES = env.get("TEST_FHIR_QUERIES", False)

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

    query_executor_username = env.get('QUERY_EXECUTOR_USERNAME', 'SPARK_JOB_SERVER')
    solr_etl_username = env.get('SOLR_ETL_USERNAME', 'SOLR_ETL')
    APPLICATIVE_USERS = [query_executor_username, solr_etl_username]
    APPLICATIVE_USERS_TOKENS = {env.get("QUERY_EXECUTOR_TOKEN"): query_executor_username,
                                env.get("SOLR_ETL_TOKEN"): solr_etl_username
                                }
