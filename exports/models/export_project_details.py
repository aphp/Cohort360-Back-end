from django.db import models
from django.db.models import CASCADE

from exports.models import ExportsBaseModel, Export


class ExportProjectDetails(ExportsBaseModel):
    export = models.OneToOneField(to=Export, related_name="project_details", on_delete=CASCADE)
    title = models.CharField(null=False, max_length=255, help_text="Project title, acronym or identifier")
    project_leader = models.CharField(
        null=False,
        max_length=255,
        help_text="Free text name of the person leading the project. Not necessarily the user who runs the export (see Export.owner)",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "export_project_details"
