from django.core.validators import MinLengthValidator
from django.db import models

from admin_cohort.models import User
from cohort.models import CohortBaseModel


class FhirFilter(CohortBaseModel):
    fhir_resource = models.CharField(max_length=255)
    fhir_version = models.CharField(max_length=50)
    name = models.CharField(max_length=50, validators=[MinLengthValidator(2)])
    filter = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fhir_filters')

    class Meta:
        unique_together = ('fhir_resource', 'name', 'owner_id')
