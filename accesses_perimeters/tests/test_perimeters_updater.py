from unittest.mock import patch

from django.db import connection
from django.db.utils import DEFAULT_DB_ALIAS
from django.db import models

from accesses.models import Perimeter
from accesses_perimeters.models import Concept, CareSite, ModelManager, APP_LABEL
from accesses_perimeters.perimeters_updater import perimeters_data_model_objects_update, psql_query_care_site_relationship
from accesses_perimeters.tests.resources.initial_data import care_sites_data, concepts_data, fact_rels_data, lists_data, ROOT_PERIMETER_ID, \
    request_query_snapshots_data, users_data, folders_data, requests_data, existing_perimeter_data
from admin_cohort.models import User
from admin_cohort.tests.tests_tools import TestCaseWithDBs
from cohort.models import RequestQuerySnapshot, Folder, Request


class FactRelationship(models.Model):
    row_id = models.BigIntegerField(primary_key=True)
    fact_id_1 = models.BigIntegerField()
    fact_id_2 = models.BigIntegerField()
    domain_concept_id_1 = models.BigIntegerField()
    domain_concept_id_2 = models.BigIntegerField()
    relationship_concept_id = models.BigIntegerField()
    delete_datetime = models.DateTimeField(null=True)
    objects = ModelManager()

    class Meta:
        app_label = APP_LABEL
        managed = False
        db_table = 'fact_relationship'


class ListCohortDef(models.Model):
    id = models.BigIntegerField(primary_key=True)
    source_type = models.CharField(blank=True, null=True, db_column='source__type')
    size = models.BigIntegerField(null=True, db_column='_size')
    source_reference_id = models.CharField(null=True, db_column='_sourcereferenceid')
    delete_datetime = models.DateTimeField(null=True)
    objects = ModelManager()

    class Meta:
        app_label = APP_LABEL
        managed = False
        db_table = 'list'


class PerimetersUpdaterTests(TestCaseWithDBs):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Concept._meta.managed = True
        CareSite._meta.managed = True
        ListCohortDef._meta.managed = True
        FactRelationship._meta.managed = True

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Concept)
            schema_editor.create_model(CareSite)
            schema_editor.create_model(ListCohortDef)
            schema_editor.create_model(FactRelationship)

    def setUp(self):
        super().setUp()
        with patch(target="accesses_perimeters.models.DB_ALIAS", new=DEFAULT_DB_ALIAS):
            for c_data in concepts_data:
                Concept.objects.create(**c_data)

            for l_vals in lists_data[1]:
                ListCohortDef.objects.create(**dict(zip(lists_data[0], l_vals)))

            for cs_vals in care_sites_data[1]:
                CareSite.objects.create(**dict(zip(care_sites_data[0], cs_vals)))

            for fr_vals in fact_rels_data[1]:
                FactRelationship.objects.create(**dict(zip(fact_rels_data[0], fr_vals)))

            for exiting_perimeter in existing_perimeter_data:
                Perimeter.objects.create(**exiting_perimeter)

            for user_data in users_data:
                User.objects.create(**user_data)

            for folder_data in folders_data:
                Folder.objects.create(**folder_data)

            for request_data in requests_data:
                request_data['parent_folder'] = Folder.objects.first()
                Request.objects.create(**request_data)

            for snapshot in request_query_snapshots_data:
                snapshot['request'] = Request.objects.first()
                RequestQuerySnapshot.objects.create(**snapshot)

            q = psql_query_care_site_relationship(top_care_site_id=ROOT_PERIMETER_ID)
            self.edited_sql_query = q.replace('omop.', '')
            self.edited_sql_care_site = CareSite.sql_get_deleted_care_sites().replace('omop.', '')

    @patch.object(CareSite, 'sql_get_deleted_care_sites')
    @patch('accesses_perimeters.perimeters_updater.psql_query_care_site_relationship')
    def test_perimeters_created_from_existing_care_sites(self, mock_sql_query, mock_sql_care_site):
        mock_sql_query.return_value = self.edited_sql_query
        mock_sql_care_site.return_value = self.edited_sql_care_site
        count_existing_perimeters = Perimeter.objects.count()
        self.assertEqual(count_existing_perimeters, 2)
        with patch(target="accesses_perimeters.models.DB_ALIAS", new=DEFAULT_DB_ALIAS):
            count_existing_care_sites = CareSite.objects.count()
            self.assertEqual(count_existing_care_sites, len(care_sites_data[1]))
            with patch('accesses_perimeters.perimeters_updater.settings') as mock_settings_2:
                mock_settings_2.ROOT_PERIMETER_ID = ROOT_PERIMETER_ID
                perimeters_data_model_objects_update()

        updated_query: RequestQuerySnapshot = RequestQuerySnapshot.objects.filter(version=2).first()
        self.assertListEqual(updated_query.perimeters_ids, ['5', '6'])
        self.assertEqual(updated_query.serialized_query, '{"sourcePopulation": {"caresiteCohortList": ["5", "6"]}}')
        count_created_perimeters = Perimeter.objects.count()
        self.assertEqual(count_created_perimeters, len(care_sites_data[1]))
