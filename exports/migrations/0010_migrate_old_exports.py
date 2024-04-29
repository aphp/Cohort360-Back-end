# written by HT on 2024-04-26 17:12
import logging

from django.db import migrations

_logger = logging.getLogger('info')


def fill_exports_table_with_export_requests(apps, schema_editor):
    export_request_model = apps.get_model('exports', 'ExportRequest')
    export_model = apps.get_model('exports', 'Export')
    datalab_model = apps.get_model('exports', 'Datalab')
    db_alias = schema_editor.connection.alias

    count = 0
    for er in export_request_model.objects.using(db_alias).all():
        datalab = None
        if er.target_unix_account:
            datalab = datalab_model.objects.using(db_alias).get(name=er.target_unix_account.name)
        export_model.objects.using(db_alias).create(data_exporter_version='3',
                                                    data_version='NA',
                                                    deleted=er.delete_datetime,
                                                    deleted_by_cascade=False,
                                                    created_at=er.insert_datetime,
                                                    modified_at=er.update_datetime,
                                                    clean_datetime=er.cleaned_at,
                                                    motivation=er.motivation,
                                                    output_format=er.output_format,
                                                    target_name=er.target_name,
                                                    target_location=er.target_location,
                                                    nominative=er.nominative,
                                                    shift_dates=er.shift_dates,
                                                    is_user_notified=er.is_user_notified,
                                                    owner_id=er.owner_id,
                                                    datalab=datalab,
                                                    request_job_duration=er.request_job_duration,
                                                    request_job_id=er.request_job_id,
                                                    request_job_status=er.request_job_status,
                                                    request_job_fail_msg=er.request_job_fail_msg)
        count += 1
    _logger.info(f'Populated {count} exports from old records')


class Migration(migrations.Migration):

    dependencies = [
        ('exports', '0009_populate_datalabs_with_unix_accounts'),
    ]

    operations = [
        migrations.RunPython(code=fill_exports_table_with_export_requests, reverse_code=migrations.RunPython.noop),
    ]
