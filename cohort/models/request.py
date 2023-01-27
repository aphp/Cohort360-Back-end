from __future__ import annotations

from functools import reduce

from django.db import models

from admin_cohort.models import CohortBaseModel, User
from cohort.models import REQUEST_DATA_TYPE_CHOICES, PATIENT_REQUEST_TYPE
# from cohort.models.dated_measure import DatedMeasure
from cohort.models.folder import Folder


# from cohort.models.request_query_snapshot import RequestQuerySnapshot


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
        # return RequestQuerySnapshot.objects.filter(request__uuid=self.uuid).latest('created_at')
        return self.query_snapshots.latest('created_at')

    def saved_snapshot(self):
        return self.query_snapshots.filter(saved=True).first()

    @property
    def dated_measures(self):
        return reduce(lambda a, b: a | b,
                      [rqs.dated_measures.all() for rqs in self.query_snapshots.all()])
                      # DatedMeasure.objects.none())

# request
# request_query_snapshot
# dated_measure
# cohort_result