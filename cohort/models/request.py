from __future__ import annotations

from functools import reduce

from django.db import models

from admin_cohort.models import User
from cohort.models import Folder, CohortBaseModel

REQUEST_DATA_TYPES = [('PATIENT', 'FHIR Patient'),
                      ('ENCOUNTER', 'FHIR Encounter')]
PATIENT_DATA_TYPE = REQUEST_DATA_TYPES[0][0]


class Request(CohortBaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_requests')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    favorite = models.BooleanField(default=False)
    parent_folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="requests", null=False)
    data_type_of_query = models.CharField(max_length=9, choices=REQUEST_DATA_TYPES, default=PATIENT_DATA_TYPE)
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='shared_requests', null=True, default=None)

    @property
    def dated_measures(self):
        return reduce(lambda a, b: a | b, [rqs.dated_measures.all() for rqs in self.query_snapshots.all()])
