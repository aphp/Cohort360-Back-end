from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction

from admin_cohort.models import User
from cohort.models import CohortBaseModel, Request


class RequestQuerySnapshotManager(models.Manager):

    def get_queryset(self):
        queryset = self._queryset_class(self.model, using=self._db)
        return queryset.exclude(cohort_results__is_subset=True)


class RequestQuerySnapshot(CohortBaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_request_query_snapshots')
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='query_snapshots')
    serialized_query = models.TextField(default="{}")
    translated_query = models.TextField(null=True)
    previous_snapshot = models.ForeignKey("RequestQuerySnapshot", related_name="next_snapshots",
                                          on_delete=models.SET_NULL, null=True)
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='shared_query_snapshots', null=True,
                                  default=None)
    perimeters_ids = ArrayField(models.CharField(max_length=15), null=True, blank=True)
    version = models.IntegerField(default=1)
    name = models.CharField(null=True, blank=True)

    # Default manager excludes some rows (e.g., subsets) from queries
    objects = RequestQuerySnapshotManager()
    # Keep a raw manager to bypass filters when needed (like row locking on save)
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
        """
        On update, optionally create a backup patch when serialized_query changes.
        """

        ### Add backup for patched queries
        uuid = str(self.uuid)
        update_fields = kwargs.get("update_fields")
        should_check_serialized = (
                update_fields is None or (
                isinstance(update_fields, (list, set, tuple)) and "serialized_query" in update_fields)
        )
        with transaction.atomic():
            # For updates, check if serialized_query has changed and create a patch
            if self.pk is not None and uuid and should_check_serialized:
                # Lock the current row to avoid race conditions on patch_version
                old = (
                    type(self).all_objects
                    .select_for_update()
                    .only("serialized_query")
                    .filter(pk=self.pk)
                    .first()
                )
                if old is not None and old.serialized_query != self.serialized_query:
                    RequestQuerySnapshotPatch.create_from_snapshot(
                        snapshot=self,
                        uuid=uuid,
                        old_serialized_query=old.serialized_query,
                    )

            super().save(*args, **kwargs)

    def restore_from_patch(self, uuid: str, patch_version: int):
        """
        Restore serialized_query from a specific patch_version for the given uuid.
        """
        patch = self.patches.get(uuid=uuid, patch_version=patch_version)
        self.serialized_query = patch.serialized_query
        # Limit DB write to the field that actually changed
        self.save(update_fields=["serialized_query"])
        return self


class RequestQuerySnapshotPatch(models.Model):
    """
    Append-only history of serialized_query for a given snapshot/uuid.

    patch_version:
        - Starts at 1 for the first patch of (snapshot, uuid)
        - Increments by 1 on each new patch
        - Independent of RequestQuerySnapshot.version
    """
    snapshot = models.ForeignKey(
        RequestQuerySnapshot,
        on_delete=models.CASCADE,
        related_name="patches",
    )
    # "uuid" that you refer to in the query structure
    uuid = models.CharField(max_length=64)

    serialized_query = models.TextField()
    patch_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("snapshot", "uuid", "patch_version")
        ordering = ["snapshot_id", "uuid", "patch_version"]

    @classmethod
    def create_from_snapshot(cls, snapshot: RequestQuerySnapshot, uuid: str, old_serialized_query: str):
        """
        Create the next patch row for this (snapshot, uuid) based on the previous max patch_version.
        """
        # Find current max patch_version for this snapshot+uuid
        last = (
            cls.objects
            .filter(snapshot=snapshot, uuid=uuid)
            .order_by("-patch_version")
            .only("patch_version")
            .first()
        )
        next_version = 1 if last is None else last.patch_version + 1

        return cls.objects.create(
            snapshot=snapshot,
            uuid=uuid,
            serialized_query=old_serialized_query,
            patch_version=next_version,
        )
