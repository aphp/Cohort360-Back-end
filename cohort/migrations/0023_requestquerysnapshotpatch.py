from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cohort", "0022_alter_string_based_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="RequestQuerySnapshotPatch",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.CharField(max_length=64)),
                ("serialized_query", models.TextField()),
                ("patch_version", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="patches",
                        to="cohort.requestquerysnapshot",
                    ),
                ),
            ],
            options={
                "ordering": ["snapshot_id", "uuid", "patch_version"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="requestquerysnapshotpatch",
            unique_together={("snapshot", "uuid", "patch_version")},
        ),
    ]
