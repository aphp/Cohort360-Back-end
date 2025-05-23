from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import UniqueConstraint, Q

from admin_cohort.models import User
from cohort.models import CohortBaseModel


class FhirFilter(CohortBaseModel):
    fhir_resource = models.CharField(max_length=255)
    fhir_version = models.CharField(max_length=50)
    query_version = models.CharField(max_length=50, default='v1.4.4')
    name = models.CharField(max_length=50, validators=[MinLengthValidator(2)])
    filter = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fhir_filters')
    identifying = models.BooleanField(default=False)
    auto_generated = models.BooleanField(default=False)

    class Meta:
        constraints = [UniqueConstraint(name='unique_name_fhir_resource_owner',
                                        fields=['name', 'fhir_resource', 'owner'],
                                        condition=Q(deleted__isnull=True))]

    def save(self, *args, **kwargs):
        self.filter = self.filter.strip('&=')
        super().save(*args, **kwargs)
