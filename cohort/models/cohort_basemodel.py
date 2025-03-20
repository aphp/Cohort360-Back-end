from uuid import uuid4

from django.db import models
from safedelete import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from admin_cohort.tools.cache import invalidate_cache


class CohortBaseModel(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, auto_created=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super(CohortBaseModel, self).save(*args, **kwargs)
        related_models = [self.__class__.__name__] + [f.related_model.__name__
                                                      for f in self.__class__._meta.fields if f.is_relation]
        for model in related_models:
            invalidate_cache(model_name=model, user=str(getattr(self, "owner_id", "")))
