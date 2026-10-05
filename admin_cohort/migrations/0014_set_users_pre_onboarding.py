from django.db import migrations

# Marks users who existed before the onboarding launch (see OnboardingStatusSerializer.is_pre_onboarding_user).
# Kept literal so the migration stays independent from the serializer code.
PRE_ONBOARDING_STEP = -1


def set_users_pre_onboarding(apps, schema_editor):
    User = apps.get_model("admin_cohort", "User")
    db_alias = schema_editor.connection.alias
    User.objects.using(db_alias).all().update(onboarding_step=PRE_ONBOARDING_STEP)


class Migration(migrations.Migration):
    dependencies = [
        ("admin_cohort", "0013_alter_user_onboarding_step"),
    ]

    operations = [
        migrations.RunPython(
            code=set_users_pre_onboarding,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
