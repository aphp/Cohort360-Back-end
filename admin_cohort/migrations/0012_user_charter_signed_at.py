from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_cohort", "0011_user_onboarding"),
    ]

    operations = [
        # Users onboarded before this migration never signed the charter: leave them null
        # rather than backfilling a signature date they did not consent to.
        migrations.AddField(
            model_name="user",
            name="charter_signed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
