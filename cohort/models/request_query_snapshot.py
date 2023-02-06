from __future__ import annotations

import json
from typing import List

from django.apps import apps
from django.contrib.postgres.fields import ArrayField
from django.db import models

from admin_cohort.models import CohortBaseModel, User
from admin_cohort.settings import SHARED_FOLDER_NAME
from cohort.models import Request, Folder


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