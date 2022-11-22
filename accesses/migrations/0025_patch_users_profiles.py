# written by HT on 2022-11-21

from django.db import migrations
from django.db.models import Count


def adjust_provider_id_for_users(apps, schema_editor):
    UserModel = apps.get_model('admin_cohort', 'User')
    ProfileModel = apps.get_model('accesses', 'Profile')
    db_alias = schema_editor.connection.alias

    # 1. update profiles having provider_id null from corresponding users having provider_id not null
    profiles_without_provider_id = ProfileModel.objects.using(db_alias).filter(provider_id__isnull=True,
                                                                               user__provider_id__isnull=False)
    for p in profiles_without_provider_id:
        p.provider_id = p.user.provider_id
        p.save()

    # 2. adjust provider_id in "user" with respect to insert_datetime asc and update corresponding profiles
    redundant_provider_id = UserModel.objects.using(db_alias).values("provider_id").\
        annotate(total=Count("provider_id")).order_by("-total").first().get("provider_id")

    users_having_same_provider_id = UserModel.objects.using(db_alias).filter(provider_id=redundant_provider_id).\
        order_by('insert_datetime')

    # the 1st user can keep his provider_id since it's already incremented
    for u in users_having_same_provider_id[1:]:
        p = ProfileModel.objects.using(db_alias).get(user_id=u.provider_username)
        u.provider_id = redundant_provider_id + 1
        p.provider_id = redundant_provider_id + 1
        u.save()
        p.save()
        redundant_provider_id += 1


class Migration(migrations.Migration):
    dependencies = [('accesses', '0023_auto_20221115_1538')]

    operations = [migrations.RunPython(code=adjust_provider_id_for_users)]
