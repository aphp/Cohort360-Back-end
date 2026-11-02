import logging
from datetime import datetime, timezone

from django.db import migrations

from admin_cohort.tools.cache import invalidate_cache

logger = logging.getLogger(__name__)

# Fixed timestamp: lets the reverse migration restore only the rows soft deleted by this migration
DELETED_AT = datetime(2026, 11, 2, 0, 0, 0, tzinfo=timezone.utc)

# Cohorts sharing a `group_id` with another owner: soft delete the one pointing to another user's list,
# so that its owner no longer sees a cohort attached to a list that is not theirs.
# UUIDs are specific to the production database: on other environments, the migration finds nothing and does nothing.
DUPLICATED_COHORTS_UUIDS = [
    "3fbe6043-592c-4486-b287-32d385286125",
    "02919221-c598-4c47-b62f-4f679894c935",
]


def soft_delete_duplicated_cohorts(apps, schema_editor):
    CohortResult = apps.get_model("cohort", "CohortResult")
    cohorts = CohortResult.objects.filter(uuid__in=DUPLICATED_COHORTS_UUIDS, deleted__isnull=True)
    found = [str(uuid) for uuid in cohorts.values_list("uuid", flat=True)]
    if not found:
        logger.info("No active cohort found among the given UUIDs, nothing to soft delete")
        return
    logger.info("Soft deleting cohort(s): %s", found)
    deleted = cohorts.update(deleted=DELETED_AT, modified_at=DELETED_AT)
    invalidate_cache(model_name="CohortResult")  # update() does not go through save(), which would invalidate the cached cohorts list
    logger.info("Soft deleted %d cohort(s)", deleted)


def restore_duplicated_cohorts(apps, schema_editor):
    CohortResult = apps.get_model("cohort", "CohortResult")
    cohorts = CohortResult.objects.filter(uuid__in=DUPLICATED_COHORTS_UUIDS, deleted=DELETED_AT)
    found = [str(uuid) for uuid in cohorts.values_list("uuid", flat=True)]
    if not found:
        logger.info("No cohort soft deleted by this migration found, nothing to restore")
        return
    logger.info("Restoring cohort(s): %s", found)
    restored = cohorts.update(deleted=None)
    invalidate_cache(model_name="CohortResult")
    logger.info("Restored %d cohort(s)", restored)


class Migration(migrations.Migration):
    dependencies = [
        ("cohort", "0026_fhirfilter_only_pdf_available"),
    ]

    operations = [
        migrations.RunPython(code=soft_delete_duplicated_cohorts, reverse_code=restore_duplicated_cohorts),
    ]
