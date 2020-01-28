# Generated by Django 2.1.7 on 2020-01-28 13:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('issue_id', models.IntegerField()),
                ('vote', models.IntegerField(choices=[(1, 'Positive vote'), (0, 'Neutral vote'), (-1, 'Negative vote')])),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='issues_users', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
