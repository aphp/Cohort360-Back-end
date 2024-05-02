# written by HT on 2024-04-26 17:02
import logging
from typing import List

from django.conf import settings
from django.db import migrations

_logger = logging.getLogger('info')


def retrieve_unix_accounts(connection) -> List[str]:
    if "workspaces" in settings.INSTALLED_APPS:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM workspaces_account;")
            accounts = [a[0] for a in cursor.fetchall()]
            return accounts
    return []


def populate_datalabs(apps, schema_editor):
    infrastructure_provider_model = apps.get_model('exports', 'InfrastructureProvider')
    datalab_model = apps.get_model('exports', 'Datalab')
    db_alias = schema_editor.connection.alias

    infra_provider = infrastructure_provider_model.objects.using(db_alias).first()
    if not infra_provider:
        infra_provider = infrastructure_provider_model.objects.using(db_alias).create(name='Main')
        
    count = 0
    for account_name in retrieve_unix_accounts(schema_editor.connection):
        datalab_model.objects.using(db_alias).create(name=account_name,
                                                     infrastructure_provider=infra_provider)
        count += 1
    _logger.info(f'Populated {count} datalab accounts')


class Migration(migrations.Migration):

    dependencies = [
        ('exports', '0008_remove_export_status_and_more'),
    ]

    operations = [
        migrations.RunPython(code=populate_datalabs, reverse_code=migrations.RunPython.noop),
    ]
