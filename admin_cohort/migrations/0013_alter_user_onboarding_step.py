from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_cohort", "0012_user_charter_signed_at"),
    ]

    operations = [
        # Allow -1, which flags users who existed before the onboarding launch.
        migrations.AlterField(
            model_name="user",
            name="onboarding_step",
            field=models.SmallIntegerField(default=0),
        ),
    ]
