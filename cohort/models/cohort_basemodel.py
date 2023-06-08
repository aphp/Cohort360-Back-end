from uuid import uuid4

from django.db import models
from safedelete import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from admin_cohort.cache_utils import flush_cache


class CohortBaseModel(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, auto_created=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super(CohortBaseModel, self).save(*args, **kwargs)
        flush_cache(model_name=self.__class__.__name__, user=self.owner_id)
