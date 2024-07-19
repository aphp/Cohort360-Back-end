from unittest import mock

from django.db import connection
from django.test import TestCase

from accesses_perimeters.models import FactRelationship
from accesses_perimeters.perimeters_retriever import PerimetersRetriever, DOMAIN_CONCEPT_ID, RELATIONSHIP_CONCEPT_ID


class PerimetersRetrieverTests(TestCase):

    def setUp(self):
        with mock.patch('accesses_perimeters.models.settings') as mock_settings:
            mock_settings.OMOP_DB_ALIAS = "default"
            FactRelationship._meta.managed = True
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(FactRelationship)

            self.fake_cohort_ids_perimeters_map = {1: [111, 1111],
                                                   2: [222],
                                                   3: [333, 3333, 33333]
                                                   }

            row_id = 1
            for cid in self.fake_cohort_ids_perimeters_map:
                for pid in self.fake_cohort_ids_perimeters_map[cid]:
                    FactRelationship.objects.create(row_id=row_id,
                                                    fact_id_1=cid,
                                                    fact_id_2=pid,
                                                    domain_concept_id_1=DOMAIN_CONCEPT_ID,
                                                    domain_concept_id_2=DOMAIN_CONCEPT_ID,
                                                    relationship_concept_id=RELATIONSHIP_CONCEPT_ID)
                    row_id += 1
            self.fake_fact_relationships = FactRelationship.objects.all()

        self.perimeters_retriever = PerimetersRetriever()
        self.fake_cohorts_ids = list(map(str, self.fake_cohort_ids_perimeters_map.keys()))

    @mock.patch("accesses_perimeters.perimeters_retriever.get_fact_relationships")
    def test_get_combined_perimeters_for_cohorts(self, mock_fact_relationships):
        mock_fact_relationships.return_value = self.fake_fact_relationships
        combined_perimeters = self.perimeters_retriever.get_virtual_cohorts(cohorts_ids=self.fake_cohorts_ids,
                                                                            group_by_cohort_id=False)
        self.assertEqual(list(combined_perimeters),
                         [e for val in self.fake_cohort_ids_perimeters_map.values() for e in val])

    @mock.patch("accesses_perimeters.perimeters_retriever.get_fact_relationships")
    def test_get_perimeters_per_cohort(self, mock_fact_relationships):
        mock_fact_relationships.return_value = self.fake_fact_relationships
        perimeters_per_cohort = self.perimeters_retriever.get_virtual_cohorts(cohorts_ids=self.fake_cohorts_ids,
                                                                              group_by_cohort_id=True)
        self.assertEqual(perimeters_per_cohort, self.fake_cohort_ids_perimeters_map)
