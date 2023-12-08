from django.core.validators import RegexValidator
from django.db import models
from django.db.models import DO_NOTHING

from exports.models import ExportsBaseModel, InfrastructureProvider


class Datalab(ExportsBaseModel):
    infrastructure_provider = models.ForeignKey(to=InfrastructureProvider, related_name="datalabs", on_delete=DO_NOTHING)
    name = models.CharField(null=False, max_length=255, unique=True, validators=[RegexValidator(regex=r' ',
                                                                                                inverse_match=True,
                                                                                                message="No spaces allowed")])

    class Meta:
        db_table = 'datalab'
