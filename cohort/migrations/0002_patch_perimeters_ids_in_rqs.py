# Generated by HT on 2023-04-11
import json

from django.conf import settings
from django.db import migrations


def fill_in_perimeters_ids_in_snapqhots(apps, schema_editor):
    rqs_model = apps.get_model('cohort', 'RequestQuerySnapshot')
    db_alias = schema_editor.connection.alias

    rqs_without_perimeters_ids = rqs_model.objects.using(db_alias).filter(perimeters_ids=None)
    for rqs in rqs_without_perimeters_ids:
        ids = []
        query = json.loads(rqs.serialized_query)
        if "sourcePopulation" in query:
            ids = query["sourcePopulation"].get("caresiteCohortList")
        elif "child" in query:
            for c in query["child"]:
                if "fhirFilter" in c and "_list" in c["fhirFilter"]:
                    ids: [str] = c["fhirFilter"].split("=")[1].split(",")

        numeric_ids = set()
        for i in ids:
            if str(i).isnumeric():
                numeric_ids.add(int(i))
        rqs.perimeters_ids = str(numeric_ids or "{}")
        rqs.save()


class Migration(migrations.Migration):

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL),
                    ('cohort', '0001_initial')
                    ]

    operations = [migrations.RunPython(fill_in_perimeters_ids_in_snapqhots)]
