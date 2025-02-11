from unittest import mock
from unittest.mock import call, MagicMock

from django.test import TestCase

from accesses.models import Perimeter
from accesses_fhir_perimeters.perimeters_updater import build_tree, FhirOrganization, perimeters_data_model_objects_update


class FhirPerimeterRetriever(TestCase):

    def assert_tree_structure(self, care_sites_tree, top_name: str):
        assert len(care_sites_tree) == 1
        assert care_sites_tree[0].id == 1
        assert care_sites_tree[0].name == top_name
        assert len(care_sites_tree[0].children) == 2
        assert care_sites_tree[0].children[0].id == 2
        assert care_sites_tree[0].children[0].name == "Hospital 1"
        assert len(care_sites_tree[0].children[0].children) == 2
        assert care_sites_tree[0].children[0].children[0].id == 4
        assert care_sites_tree[0].children[0].children[0].name == "Service 1.1"
        assert care_sites_tree[0].children[0].children[0].children[0].id == 8
        assert care_sites_tree[0].children[0].children[0].children[0].name == "Service 1.1.1"
        assert care_sites_tree[0].children[0].children[1].id == 5
        assert care_sites_tree[0].children[0].children[1].name == "Service 1.2"
        assert care_sites_tree[0].children[1].id == 3
        assert care_sites_tree[0].children[1].name == "Hospital 2"
        assert len(care_sites_tree[0].children[1].children) == 2
        assert care_sites_tree[0].children[1].children[0].id == 6
        assert care_sites_tree[0].children[1].children[0].name == "Service 2.1"
        assert care_sites_tree[0].children[1].children[1].id == 7
        assert care_sites_tree[0].children[1].children[1].name == "Service 2.2"

    def test_tree_building(self):
        care_sites = {
            1: FhirOrganization(
                id=1,
                name="All Hospitals"
            ),
            2: FhirOrganization(id=2, name="Hospital 1", part_of=1),
            3: FhirOrganization(id=3, name="Hospital 2", part_of=1),
            4: FhirOrganization(id=4, name="Service 1.1", part_of=2),
            5: FhirOrganization(id=5, name="Service 1.2", part_of=2),
            6: FhirOrganization(id=6, name="Service 2.1", part_of=3),
            7: FhirOrganization(id=7, name="Service 2.2", part_of=3),
            8: FhirOrganization(id=8, name="Service 1.1.1", part_of=4)
        }
        care_sites_tree = build_tree(care_sites, main_root_default=FhirOrganization(id=1, name="All Hospitals default"))
        self.assert_tree_structure(care_sites_tree, "All Hospitals")

    def test_tree_building_with_default_root(self):
        care_sites = {
            2: FhirOrganization(id=2, name="Hospital 1"),
            3: FhirOrganization(id=3, name="Hospital 2"),
            4: FhirOrganization(id=4, name="Service 1.1", part_of=2),
            5: FhirOrganization(id=5, name="Service 1.2", part_of=2),
            6: FhirOrganization(id=6, name="Service 2.1", part_of=3),
            7: FhirOrganization(id=7, name="Service 2.2", part_of=3),
            8: FhirOrganization(id=8, name="Service 1.1.1", part_of=4)
        }
        care_sites_tree = build_tree(care_sites, main_root_default=FhirOrganization(id=1, name="All Hospitals default"))
        self.assert_tree_structure(care_sites_tree, "All Hospitals default")

    @mock.patch('accesses_fhir_perimeters.perimeters_updater.get_organization_care_sites')
    @mock.patch('accesses_fhir_perimeters.tasks.create_virtual_cohort')
    def test_perimeters_created_from_existing_care_sites(self, mock_create_virtual_cohort: MagicMock, mock_get_organization_care_sites: MagicMock):
        for perimeter in [
            {'id': 9999, 'name': 'APHP', 'source_value': 'APHP', 'short_name': 'AP-HP', 'local_id': 'Local APHP', 'type_source_value': 'AP-HP',
             'parent_id': None, 'level': 1, 'above_levels_ids': '', 'inferior_levels_ids': '0,1,2', 'cohort_id': '9999'},
            {'id': 0, 'name': 'P0', 'source_value': 'P0', 'short_name': 'P0', 'local_id': 'Local P0', 'type_source_value': 'Groupe hospitalier (GH)',
             'parent_id': 9999, 'level': 2, 'above_levels_ids': '9999', 'inferior_levels_ids': '3,4,5', 'cohort_id': '0'},
            {'id': 1, 'name': 'P1', 'source_value': 'P1', 'short_name': 'P1', 'local_id': 'Local P1', 'type_source_value': 'Groupe hospitalier (GH)',
             'parent_id': 9999, 'level': 2, 'above_levels_ids': '9999', 'inferior_levels_ids': '6,7', 'cohort_id': '1'},
            {'id': 2, 'name': 'P2', 'source_value': 'P2', 'short_name': 'P2', 'local_id': 'Local P2', 'type_source_value': 'Groupe hospitalier (GH)',
             'parent_id': 9999, 'level': 2, 'above_levels_ids': '9999', 'inferior_levels_ids': '8,9,10', 'cohort_id': '2'},
            {'id': 3, 'name': 'P3', 'source_value': 'P3', 'short_name': 'P3', 'local_id': 'Local P3', 'type_source_value': 'Hôpital', 'parent_id': 0,
             'level': 3, 'above_levels_ids': '0,9999', 'cohort_id': '3'}]:
            Perimeter.objects.create(**perimeter)

        mock_get_organization_care_sites.return_value = {
            9999: FhirOrganization(id=9999, name="All Hospitals"),
            2: FhirOrganization(id=2, name="Hospital 1", part_of=9999),
            3: FhirOrganization(id=3, name="Hospital 2", part_of=9999),
            4: FhirOrganization(id=4, name="Service 1.1", part_of=2),
            5: FhirOrganization(id=5, name="Service 1.2", part_of=2),
            6: FhirOrganization(id=6, name="Service 2.1", part_of=3),
            7: FhirOrganization(id=7, name="Service 2.2", part_of=3),
            8: FhirOrganization(id=8, name="Service 1.1.1", part_of=4)
        }

        count_existing_perimeters = Perimeter.objects.count()
        self.assertEqual(count_existing_perimeters, 5)

        perimeters_data_model_objects_update()

        count_created_perimeters = Perimeter.objects.all().count()
        self.assertEqual(count_created_perimeters, 8)
        mock_create_virtual_cohort.s.assert_has_calls(calls=[
            call('4', ['8']),
            call('5', []),
            call('6', []),
            call('7', []),
            call('8', []),
            call('3', ['6', '7'], 3),
            call('2', ['4', '5', '8'], 2),
            call('9999', ['2', '3', '4', '5', '6', '7', '8'], 9999)
        ], any_order=True)
        deleted_perimeters = Perimeter.objects.exclude(delete_datetime__isnull=True).values_list('id', flat=True)
        assert len(deleted_perimeters) == 2
        assert 0 in deleted_perimeters
        assert 1 in deleted_perimeters
