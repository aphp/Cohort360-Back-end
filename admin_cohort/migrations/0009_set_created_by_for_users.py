import json

from django.conf import settings
from django.db import migrations


def set_creator_for_existing_users(apps, schema_editor):
    APIRequestLog = apps.get_model('rest_framework_tracking', 'APIRequestLog')
    User = apps.get_model('admin_cohort', 'User')
    db_alias = schema_editor.connection.alias

    create_user_logs = (
        APIRequestLog.objects.using(db_alias)
        .filter(method="POST", view_method="create", status_code="201",
                view__icontains="admin_cohort.views.user")
        .order_by("requested_at")
        .values("user_id", "response")
    )
    for log in create_user_logs:
        try:
            response = json.loads(log.get("response") or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        created_username = response.get("username")
        creator_id = log.get("user_id")
        if not created_username or not creator_id:
            continue
        user = User.objects.using(db_alias).filter(pk=created_username).first()
        if user and not user.created_by_id:
            user.created_by_id = creator_id
            user.save(update_fields=["created_by_id"])


def set_last_updater_for_existing_users(apps, schema_editor):
    APIRequestLog = apps.get_model('rest_framework_tracking', 'APIRequestLog')
    User = apps.get_model('admin_cohort', 'User')
    db_alias = schema_editor.connection.alias

    update_user_logs = (
        APIRequestLog.objects.using(db_alias)
        .filter(method="PATCH", view_method="partial_update", status_code="200",
                view__icontains="admin_cohort.views.user")
        .order_by("requested_at")
        .values("user_id", "response")
    )
    users_updaters = {}
    for log in update_user_logs:
        try:
            response = json.loads(log.get("response") or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        updated_username = response.get("username")
        updater_id = log.get("user_id")
        if updated_username and updater_id:
            users_updaters[updated_username] = updater_id

    for username, updater_id in users_updaters.items():
        user = User.objects.using(db_alias).filter(pk=username).first()
        if user:
            user.updated_by_id = updater_id
            user.save(update_fields=["updated_by_id"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('admin_cohort', '0008_user_created_by'),
        ('rest_framework_tracking', '0011_auto_20201117_2016'),
    ]

    operations = [
        migrations.RunPython(
            code=set_creator_for_existing_users,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=set_last_updater_for_existing_users,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
