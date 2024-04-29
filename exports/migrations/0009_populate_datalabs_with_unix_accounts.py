# written by HT on 2024-04-26 17:02
import logging

from django.db import migrations


_logger = logging.getLogger('info')


def populate_datalabs(apps, schema_editor):
    infrastructure_provider_model = apps.get_model('exports', 'InfrastructureProvider')
    datalab_model = apps.get_model('exports', 'Datalab')
    account_model = apps.get_model('workspaces', 'Account')
    db_alias = schema_editor.connection.alias

    infra_provider = infrastructure_provider_model.objects.using(db_alias).first()
    if not infra_provider:
        infra_provider = infrastructure_provider_model.objects.using(db_alias).create(name='Main')
        
    count = 0
    for account_name in account_model.objects.using(db_alias).all().values_list('name', flat=True):
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
