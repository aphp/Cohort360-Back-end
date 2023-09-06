from __future__ import annotations

import json

from django.contrib.postgres.fields import ArrayField
from django.db import models

from admin_cohort.models import User
from cohort.models import CohortBaseModel, Request


class RequestQuerySnapshot(CohortBaseModel):
    title = models.CharField(default="", max_length=50)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_request_query_snapshots')
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='query_snapshots')
    serialized_query = models.TextField(default="{}")
    previous_snapshot = models.ForeignKey("RequestQuerySnapshot", related_name="next_snapshots", on_delete=models.SET_NULL, null=True)
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='shared_query_snapshots', null=True, default=None)
    perimeters_ids = ArrayField(models.CharField(max_length=15), null=True, blank=True)
    version = models.IntegerField(default=1)

    @property
    def has_linked_cohorts(self):
        return bool(self.cohort_results.all())

    def save(self, *args, **kwargs):
        try:
            json.loads(str(self.serialized_query))
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f"serialized_query is not a valid JSON {e}")
        super(RequestQuerySnapshot, self).save(*args, **kwargs)
