from django.db import migrations, models
from django.utils import timezone

# Number of macro steps in the onboarding journey at the time of this migration.
# Kept literal so the migration stays independent from the model code.
ONBOARDING_TOTAL_STEPS = 3


def mark_existing_users_onboarded(apps, schema_editor):
    User = apps.get_model('admin_cohort', 'User')
    db_alias = schema_editor.connection.alias
    User.objects.using(db_alias).filter(onboarding_completed_at__isnull=True, delete_datetime__isnull=True).update(
        onboarding_step=ONBOARDING_TOTAL_STEPS,
        onboarding_completed_at=timezone.now(),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('admin_cohort', '0010_maintenancephase_is_data_saved_message_hidden'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='onboarding_step',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='onboarding_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            code=mark_existing_users_onboarded,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
