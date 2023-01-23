from __future__ import annotations

import json
from functools import reduce
from typing import List

from django.apps import apps
from django.contrib.postgres.fields import ArrayField
from django.db import models

from admin_cohort.models import CohortBaseModel
from admin_cohort.models import User, JobModel
from admin_cohort.settings import SHARED_FOLDER_NAME

COHORT_TYPE_CHOICES = [("IMPORT_I2B2", "Previous cohorts imported from i2b2.",),
                       ("MY_ORGANIZATIONS", "Organizations in which I work (care sites "
                                            "with pseudo-anonymised reading rights).",),
                       ("MY_PATIENTS", "Patients that passed by all my organizations "
                                       "(care sites with nominative reading rights)."),
                       ("MY_COHORTS", "Cohorts I created in Cohort360")]

I2B2_COHORT_TYPE = COHORT_TYPE_CHOICES[0][0]
MY_ORGANISATIONS_COHORT_TYPE = COHORT_TYPE_CHOICES[1][0]
MY_PATIENTS_COHORT_TYPE = COHORT_TYPE_CHOICES[2][0]
MY_COHORTS_COHORT_TYPE = COHORT_TYPE_CHOICES[3][0]

REQUEST_DATA_TYPE_CHOICES = [('PATIENT', 'FHIR Patient'),
                             ('ENCOUNTER', 'FHIR Encounter')]
PATIENT_REQUEST_TYPE = REQUEST_DATA_TYPE_CHOICES[0][0]

SNAPSHOT_DM_MODE = "Snapshot"
GLOBAL_DM_MODE = "Global"
DATED_MEASURE_MODE_CHOICES = [(SNAPSHOT_DM_MODE, SNAPSHOT_DM_MODE),
                              (GLOBAL_DM_MODE, GLOBAL_DM_MODE)]


class Folder(CohortBaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.owner})"

    def __repr__(self):
        return f"Folder {self})"


class Request(CohortBaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_requests')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    favorite = models.BooleanField(default=False)
    parent_folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="requests", null=False)
    data_type_of_query = models.CharField(max_length=9, choices=REQUEST_DATA_TYPE_CHOICES, default=PATIENT_REQUEST_TYPE)
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='shared_requests', null=True,
                                  default=None)

    def last_request_snapshot(self):
        return RequestQuerySnapshot.objects.filter(request__uuid=self.uuid).latest('created_at')

    def saved_snapshot(self):
        return self.query_snapshots.filter(saved=True).first()

    @property
    def dated_measures(self):
        return reduce(lambda a, b: a | b,
                      [rqs.dated_measures.all() for rqs in self.query_snapshots.all()],
                      DatedMeasure.objects.none())


class RequestQuerySnapshot(CohortBaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_request_query_snapshots')
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='query_snapshots')
    serialized_query = models.TextField(default="{}")
    previous_snapshot = models.ForeignKey("RequestQuerySnapshot", related_name="next_snapshots",
                                          on_delete=models.SET_NULL, null=True)
    is_active_branch = models.BooleanField(default=True)
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='shared_query_snapshots',
                                  null=True, default=None)
    # unused, untested
    saved = models.BooleanField(default=False)
    refresh_every_seconds = models.BigIntegerField(default=0)
    refresh_create_cohort = models.BooleanField(default=False)
    perimeters_ids = ArrayField(models.CharField(max_length=15), null=True, blank=True)

    @property
    def active_next_snapshot(self):
        rqs_model = apps.get_model('cohort', 'RequestQuerySnapshot')
        next_snapshots = rqs_model.objects.filter(previous_snapshot=self)
        return next_snapshots.filter(is_active_branch=True).first()

    def share(self, recipients: List[User], name: str) -> RequestQuerySnapshot:
        dct_recipients = dict([(r.pk, r) for r in recipients])
        folders = list(Folder.objects.filter(owner__in=recipients, name=SHARED_FOLDER_NAME))
        owners_ids = [folder.owner.pk for folder in folders]
        folders_to_create = [Folder(owner=r, name=SHARED_FOLDER_NAME) for r in recipients if r.pk not in owners_ids]
        dct_folders = dict([(f.owner.pk, f) for f in folders + folders_to_create])
        request_name = name or self.request.name

        requests = [Request(**{**dict([(field.name, getattr(self.request, field.name))
                                       for field in Request._meta.fields if field.name != Request._meta.pk.name]),
                               'owner': dct_recipients[o],
                               'favorite': False,
                               'name': request_name,
                               'shared_by': self.owner,
                               'parent_folder': f
                               })
                    for (o, f) in dct_folders.items()]

        dct_requests = dict([(r.owner.pk, r) for r in requests])

        rqss = [RequestQuerySnapshot(**{**dict([(field.name, getattr(self, field.name))
                                                for field in RequestQuerySnapshot._meta.fields
                                                if field.name != RequestQuerySnapshot._meta.pk.name]),
                                        'shared_by': self.owner,
                                        'owner': dct_recipients[o],
                                        'previous_snapshot': None,
                                        'is_active_branch': True,
                                        'saved': False,
                                        'refresh_every_seconds': 0,
                                        'refresh_create_cohort': False,
                                        'request': r
                                        })
                for (o, r) in dct_requests.items()]

        Folder.objects.bulk_create(folders_to_create)
        Request.objects.bulk_create(requests)
        created = RequestQuerySnapshot.objects.bulk_create(rqss)
        return created

    def save(self, *args, **kwargs):
        try:
            json.loads(str(self.serialized_query))
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f"serialized_query is not a valid JSON {e}")
        super(RequestQuerySnapshot, self).save(*args, **kwargs)

    def save_snapshot(self):
        previous_saved = self.request.saved_snapshot
        if previous_saved is not None:
            previous_saved.saved = False
            previous_saved.save()
        self.saved = True
        self.save()


class DatedMeasure(CohortBaseModel, JobModel):
    """
    This is an intermediary result giving only limited info before
    possibly generating a Cohort/Group in Fhir.
    """
    # todo : fix this, user_request_query_results is wrong
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_request_query_results')
    request_query_snapshot = models.ForeignKey(RequestQuerySnapshot, on_delete=models.CASCADE,
                                               related_name='dated_measures')
    fhir_datetime = models.DateTimeField(null=True, blank=False)
    # Size of potential cohort as returned by SolR
    measure = models.BigIntegerField(null=True, blank=False)
    measure_min = models.BigIntegerField(null=True, blank=False)
    measure_max = models.BigIntegerField(null=True, blank=False)
    count_task_id = models.TextField(blank=True)
    mode = models.CharField(max_length=20, choices=DATED_MEASURE_MODE_CHOICES, default=SNAPSHOT_DM_MODE, null=True)


class CohortResult(CohortBaseModel, JobModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_cohorts')
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    favorite = models.BooleanField(default=False)
    request_query_snapshot = models.ForeignKey(RequestQuerySnapshot, on_delete=models.CASCADE,
                                               related_name='cohort_results')
    fhir_group_id = models.CharField(max_length=64, blank=True)
    dated_measure = models.ForeignKey(DatedMeasure, related_name="cohort", on_delete=models.CASCADE)
    dated_measure_global = models.ForeignKey(DatedMeasure, related_name="restricted_cohort", null=True,
                                             on_delete=models.SET_NULL)
    create_task_id = models.TextField(blank=True)

    # will depend on the right (pseudo-anonymised or nominative) you
    # have on the care_site
    # unused untested
    type = models.CharField(max_length=20, choices=COHORT_TYPE_CHOICES, default=MY_COHORTS_COHORT_TYPE)

    @property
    def result_size(self):
        return self.dated_measure.measure
