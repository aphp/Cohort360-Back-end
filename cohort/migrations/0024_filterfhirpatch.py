from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cohort", "0023_requestquerysnapshotpatch"),
    ]

    operations = [
        migrations.CreateModel(
            name="FilterFhirPatch",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.CharField(max_length=64)),
                ("filter", models.TextField()),
                ("patch_version", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "filter_fhir",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="patches",
                        to="cohort.fhirfilter",
                    ),
                ),
            ],
            options={
                "ordering": ["filter_fhir_id", "uuid", "patch_version"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="filterfhirpatch",
            unique_together={("filter_fhir", "uuid", "patch_version")},
        ),
    ]
