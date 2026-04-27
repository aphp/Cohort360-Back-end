from django.core.validators import MinLengthValidator
from django.db import models, transaction
from django.db.models import UniqueConstraint, Q

from admin_cohort.models import User
from cohort.models import CohortBaseModel


class FhirFilter(CohortBaseModel):
    fhir_resource = models.CharField(max_length=255)
    fhir_version = models.CharField(max_length=50)
    query_version = models.CharField(max_length=50, default="v1.4.4")
    name = models.CharField(max_length=50, validators=[MinLengthValidator(2)])
    filter = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fhir_filters")
    identifying = models.BooleanField(default=False)
    auto_generated = models.BooleanField(default=False)

    # Keep a raw manager to bypass any default filters when needed (e.g., row locking on save)
    all_objects = models.Manager()  # type: ignore[misc, assignment]

    class Meta:
        constraints = [
            UniqueConstraint(name="unique_name_fhir_resource_owner", fields=["name", "fhir_resource", "owner"], condition=Q(deleted__isnull=True))
        ]

    def save(self, *args, **kwargs):
        self.filter = self.filter.strip("&=")
        uuid = str(self.uuid)
        update_fields = kwargs.get("update_fields")
        should_check_serialized = update_fields is None or (isinstance(update_fields, (list, set, tuple)) and "filter" in update_fields)
        with transaction.atomic():
            # For updates, check if filter has changed and create a patch
            if self.pk is not None and uuid and should_check_serialized:
                # Lock the current row to avoid race conditions on patch_version
                old = type(self).all_objects.select_for_update().only("filter").filter(pk=self.pk).first()
                if old is not None and old.filter != self.filter:
                    FilterFhirPatch.create_from_snapshot(
                        filter_fhir=self,
                        uuid=uuid,
                        old_filter=old.filter,
                    )
            super().save(*args, **kwargs)

    def restore_from_patch(self, uuid: str, patch_version: int):
        """
        Restore filter from a specific patch_version for the given uuid.
        """
        patch = self.patches.get(uuid=uuid, patch_version=patch_version)
        self.filter = patch.filter
        self.save(update_fields=["filter"])
        return self


class FilterFhirPatch(models.Model):
    filter_fhir = models.ForeignKey(
        FhirFilter,
        on_delete=models.CASCADE,
        related_name="patches",
    )
    uuid = models.CharField(max_length=64)
    filter = models.TextField()
    patch_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("filter_fhir", "uuid", "patch_version")
        # Keep ordering aligned with RequestQuerySnapshotPatch for consistency
        ordering = ["filter_fhir_id", "uuid", "patch_version"]

    @classmethod
    def create_from_snapshot(cls, filter_fhir: FhirFilter, uuid: str, old_filter: str):
        """
        Create the next patch row for this (snapshot, uuid) based on the previous max patch_version.
        """
        # Find current max patch_version for this filter_fhir+uuid
        last = cls.objects.filter(filter_fhir=filter_fhir, uuid=uuid).order_by("-patch_version").only("patch_version").first()
        next_version = 1 if last is None else last.patch_version + 1

        return cls.objects.create(
            filter_fhir=filter_fhir,
            uuid=uuid,
            filter=old_filter,
            patch_version=next_version,
        )
