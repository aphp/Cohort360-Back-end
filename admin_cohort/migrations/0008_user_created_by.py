from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admin_cohort', '0007_user_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                db_column='created_by',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_users',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                db_column='updated_by',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='updated_users',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
