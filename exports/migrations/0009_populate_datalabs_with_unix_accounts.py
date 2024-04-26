# written by HT on 2024-04-26 17:02

from django.db import migrations, models


populate_datalabs = "INSERT INTO datalab (name) SELECT username FROM workspaces_account;"


class Migration(migrations.Migration):

    dependencies = [
        ('exports', '0008_remove_export_status_and_more'),
    ]

    operations = [
        migrations.RunSQL(sql=populate_datalabs, reverse_sql=migrations.RunSQL.noop),
    ]
