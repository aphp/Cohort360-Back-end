import json
from typing import List

from celery import shared_task

from accesses_fhir_perimeters.perimeters_updater import perimeters_data_model_objects_update
from admin_cohort import celery_app
from cohort_job_server.cohort_creator import CohortCreator

ADMIN_USERNAME = "admin"


@celery_app.task()
def perimeters_daily_update():
    perimeters_data_model_objects_update()


def create_virtual_cohort_query(perimeter_id: str) -> str:
    return json.dumps(
        {
            "_type": "request",
            "request": {
                "_id": 0,
                "_type": "andGroup",
                "criteria": [
                    {
                        "_id": 1,
                        "_type": "basicResource",
                        "criteria": [],
                        "dateRangeList": [],
                        "filterFhir": f"service-provider={perimeter_id}",
                        "isInclusive": True,
                        "resourceType": "Encounter",
                        "temporalConstraints": []
                    }
                ],
                "dateRangeList": [],
                "isInclusive": True,
                "temporalConstraints": []
            },
            "sourcePopulation": {},
            "temporalConstraints": []
        })


@shared_task
def create_virtual_cohort(perimeter_id: str, children_level_ids: List[str], existing_cohort_id: int = None):
    CohortCreator().launch_cohort_creation(cohort_id=None,
                                           json_query=create_virtual_cohort_query(",".join([perimeter_id] + children_level_ids)),
                                           auth_headers={},
                                           callback_path=f"/fhir-perimeters/{perimeter_id}/",
                                           owner_username=ADMIN_USERNAME,
                                           existing_cohort_id=existing_cohort_id
                                           )
