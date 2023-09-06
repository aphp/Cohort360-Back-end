from uuid import uuid4

from django.db import models
from safedelete import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from admin_cohort.tools.cache import invalidate_cache


class ExportsBaseModel(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, auto_created=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super(ExportsBaseModel, self).save(*args, **kwargs)
        invalidate_cache(model_name=self.__class__.__name__)
