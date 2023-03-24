from __future__ import annotations

from functools import reduce

from django.db import models

from admin_cohort.models import User
from cohort.models import Folder, CohortBaseModel

COHORT_TYPE_CHOICES = [("IMPORT_I2B2", "Previous cohorts imported from i2b2.",),
                       ("MY_ORGANIZATIONS", "Organizations in which I work (care sites "
                                            "with pseudo-anonymised reading rights).",),
                       ("MY_PATIENTS", "Patients that passed by all my organizations "
                                       "(care sites with nominative reading rights)."),
                       ("MY_COHORTS", "Cohorts I created in Cohort360")]

MY_COHORTS_COHORT_TYPE = COHORT_TYPE_CHOICES[3][0]

REQUEST_DATA_TYPE_CHOICES = [('PATIENT', 'FHIR Patient'),
                             ('ENCOUNTER', 'FHIR Encounter')]
PATIENT_REQUEST_TYPE = REQUEST_DATA_TYPE_CHOICES[0][0]


class Request(CohortBaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_requests')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    favorite = models.BooleanField(default=False)
    parent_folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="requests", null=False)
    data_type_of_query = models.CharField(max_length=9, choices=REQUEST_DATA_TYPE_CHOICES, default=PATIENT_REQUEST_TYPE)
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='shared_requests', null=True, default=None)

    @property
    def dated_measures(self):
        return reduce(lambda a, b: a | b, [rqs.dated_measures.all() for rqs in self.query_snapshots.all()])
