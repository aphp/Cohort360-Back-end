from unittest import mock

from django.db import connection
from django.test import TestCase

from accesses_perimeters.models import Concept, CareSite
#from accesses_perimeters.perimeters_updater import perimeters_data_model_objects_update


class PerimetersUpdaterTests(TestCase):

    def setUp(self):
        with mock.patch('accesses_perimeters.models.settings') as mock_settings:
            mock_settings.OMOP_DB_ALIAS = "default"
            Concept._meta.managed = True
            CareSite._meta.managed = True
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(Concept)
                schema_editor.create_model(CareSite)

            self.concepts = Concept.objects.all()

            # create Concept objects
            # create CareSite objects (some of which to be deleted, others new)


