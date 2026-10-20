import json
import tempfile
from datetime import timedelta
from io import StringIO
from unittest import mock
from unittest.mock import call, MagicMock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from fhirpy import SyncFHIRClient
from fhirpy.base.exceptions import OperationOutcome

from accesses.models import Perimeter
from accesses_fhir_perimeters.perimeters_updater import (
    build_tree,
    FhirOrganization,
    perimeters_data_model_objects_update,
    PerimetersSyncAborted,
    get_organization_care_sites,
    get_fhir_client,
    compute_perimeters_sync,
    get_perimeter_lists,
    PerimeterList,
    LIST_TOTAL_EXTENSION_URL,
)

APHP, GH, HOPITAL, POLE, UF = "AP-HP", "Groupe hospitalier (GH)", "Hôpital", "Pôle/DMU", "Unité Fonctionnelle (UF)"
PERIMETER_TYPES = [APHP, "GHU", HOPITAL, GH, POLE, UF]
ORG_TYPE_SYSTEM = "http://fhir.eds.aphp.fr/fhir/CodeSystem/organization-type"

fhir_client = SyncFHIRClient("http://fhir.test")


def fhir_org(org_id, name, type_code, part_of=None, alias=None):
    """An Organization shaped like FhirApi's (OrganizationMapper)"""
    data = {
        "id": str(org_id),
        "active": True,
        "name": name,
        "type": [{"coding": [{"system": ORG_TYPE_SYSTEM, "code": "prov"}]}, {"coding": [{"system": ORG_TYPE_SYSTEM, "code": type_code}]}],
    }
    if part_of is not None:
        data["partOf"] = {"reference": f"Organization/{part_of}"}
    if alias:
        data["alias"] = [alias]
    return fhir_client.resource("Organization", **data)


def fhir_list(list_id, source, total=None):
    """A List shaped like FhirApi's (ListSearch): one per care site, with its patient count"""
    data = {"id": str(list_id), "status": "current", "mode": "snapshot", "source": {"reference": source}}
    if total is not None:
        data["extension"] = [{"url": LIST_TOTAL_EXTENSION_URL, "valueInteger": total}]
    return fhir_client.resource("List", **data)


def care_site(cs_id, name, type_source_value, part_of=None, source_value=None):
    return FhirOrganization(id=cs_id, name=name, part_of=part_of, type_source_value=type_source_value, source_value=source_value or f"S{cs_id}")


@override_settings(PERIMETER_TYPES=PERIMETER_TYPES)
class FhirOrganizationsFetchTest(TestCase):
    @mock.patch("accesses_fhir_perimeters.perimeters_updater.get_fhir_client")
    @mock.patch("accesses_fhir_perimeters.perimeters_updater.fetch_organizations")
    def test_parse_organizations(self, mock_fetch: MagicMock, _):
        mock_fetch.return_value = [
            fhir_org(1, "AP-HP", APHP, alias="APHP"),
            fhir_org(2, "GH 1", GH, part_of=1, alias="H01"),
            fhir_org(3, "UH 1", "Unité d’hébergement (UH)", part_of=2),
            fhir_org("abc", "Bad id", HOPITAL, part_of=2),
        ]
        care_sites = get_organization_care_sites()
        self.assertEqual(sorted(care_sites), [1, 2])
        self.assertIsNone(care_sites[1].part_of)
        self.assertEqual(care_sites[2].part_of, 1)
        self.assertEqual(care_sites[2].type_source_value, GH)
        self.assertEqual(care_sites[2].source_value, "H01")

    @mock.patch("accesses_fhir_perimeters.perimeters_updater.get_fhir_client")
    @mock.patch("accesses_fhir_perimeters.perimeters_updater.fetch_organizations")
    def test_retry_with_new_system_token(self, mock_fetch: MagicMock, mock_client: MagicMock):
        mock_fetch.side_effect = [OperationOutcome(reason="401"), [fhir_org(1, "AP-HP", APHP)]]
        self.assertEqual(list(get_organization_care_sites()), [1])
        mock_client.assert_has_calls([call(), call(force_system_token=True)])

    @mock.patch("accesses_fhir_perimeters.perimeters_updater.jwt_auth_service")
    def test_static_token_overrides_system_token(self, mock_jwt: MagicMock):
        with mock.patch("accesses_fhir_perimeters.perimeters_updater.AccessesFhirAuxConfig.FHIR_ACCESS_TOKEN", "static"):
            get_fhir_client()
            mock_jwt.generate_system_token.assert_not_called()
            get_fhir_client(force_system_token=True)
            mock_jwt.generate_system_token.assert_called_once()

    @mock.patch("accesses_fhir_perimeters.perimeters_updater.jwt_auth_service")
    def test_system_token_by_default(self, mock_jwt: MagicMock):
        with mock.patch("accesses_fhir_perimeters.perimeters_updater.AccessesFhirAuxConfig.FHIR_ACCESS_TOKEN", ""):
            get_fhir_client()
            mock_jwt.generate_system_token.assert_called_once()


class FhirListsFetchTest(TestCase):
    @mock.patch("accesses_fhir_perimeters.perimeters_updater.get_fhir_client")
    @mock.patch("accesses_fhir_perimeters.perimeters_updater.fetch_lists")
    def test_parse_lists(self, mock_fetch: MagicMock, _):
        mock_fetch.return_value = [
            fhir_list(111, "Organization/1", total=1500),
            fhir_list(112, "Organization/2"),
            fhir_list(113, "Practitioner/3", total=5),
            fhir_list(114, "Organization/abc", total=5),
        ]
        self.assertEqual(
            get_perimeter_lists(),
            {1: PerimeterList(cohort_id="111", cohort_size="1500"), 2: PerimeterList(cohort_id="112", cohort_size=None)},
        )

    @mock.patch("accesses_fhir_perimeters.perimeters_updater.get_fhir_client")
    @mock.patch("accesses_fhir_perimeters.perimeters_updater.fetch_lists")
    def test_lists_retry_with_new_system_token(self, mock_fetch: MagicMock, mock_client: MagicMock):
        mock_fetch.side_effect = [OperationOutcome(reason="401"), [fhir_list(111, "Organization/1", total=10)]]
        self.assertEqual(list(get_perimeter_lists()), [1])
        mock_client.assert_has_calls([call(), call(force_system_token=True)])


class BuildTreeTest(TestCase):
    def test_tree_building(self):
        care_sites = {
            1: care_site(1, "All Hospitals", APHP),
            2: care_site(2, "Hospital 1", HOPITAL, part_of=1),
            3: care_site(3, "Hospital 2", HOPITAL, part_of=1),
            4: care_site(4, "Service 1.1", POLE, part_of=2),
            5: care_site(5, "Service 1.2", POLE, part_of=2),
            8: care_site(8, "Service 1.1.1", UF, part_of=4),
            9: care_site(9, "Orphan", POLE, part_of=404),
            10: care_site(10, "Orphan child", UF, part_of=9),
        }
        root, orphans = build_tree(care_sites, root_id=1)
        self.assertEqual(root.id, 1)
        self.assertEqual([c.id for c in root.children], [2, 3])
        self.assertEqual([c.id for c in root.children[0].children], [4, 5])
        self.assertEqual([c.id for c in root.children[0].children[0].children], [8])
        self.assertEqual(sorted(o.id for o in orphans), [9, 10])

    def test_missing_root_aborts(self):
        with self.assertRaises(PerimetersSyncAborted):
            build_tree({2: care_site(2, "Hospital 1", HOPITAL)}, root_id=1)


@override_settings(PERIMETER_TYPES=PERIMETER_TYPES, ROOT_PERIMETER_ID=9999)
@mock.patch("accesses_fhir_perimeters.perimeters_updater.get_organization_care_sites")
class PerimetersUpdateTest(TestCase):
    def setUp(self):
        lists_patcher = mock.patch("accesses_fhir_perimeters.perimeters_updater.get_perimeter_lists", side_effect=self.fhir_lists)
        self.mock_lists = lists_patcher.start()
        self.addCleanup(lists_patcher.stop)
        for perimeter in [
            {
                "id": 9999,
                "name": "APHP",
                "source_value": "APHP",
                "short_name": "AP-HP",
                "type_source_value": APHP,
                "parent_id": None,
                "level": 1,
                "above_levels_ids": "",
                "inferior_levels_ids": "0,1,2",
                "cohort_id": "9999",
            },
            {
                "id": 0,
                "name": "P0",
                "source_value": "P0",
                "short_name": "P0",
                "type_source_value": GH,
                "parent_id": 9999,
                "level": 2,
                "above_levels_ids": "9999",
                "inferior_levels_ids": "3,4,5",
                "cohort_id": "0",
            },
            {
                "id": 1,
                "name": "P1",
                "source_value": "P1",
                "short_name": "P1",
                "type_source_value": GH,
                "parent_id": 9999,
                "level": 2,
                "above_levels_ids": "9999",
                "inferior_levels_ids": "6,7",
                "cohort_id": "1",
            },
            {
                "id": 2,
                "name": "P2",
                "source_value": "P2",
                "short_name": "P2",
                "type_source_value": GH,
                "parent_id": 9999,
                "level": 2,
                "above_levels_ids": "9999",
                "inferior_levels_ids": "8,9,10",
                "cohort_id": "2",
            },
            {
                "id": 3,
                "name": "P3",
                "source_value": "P3",
                "short_name": "P3",
                "type_source_value": HOPITAL,
                "parent_id": 0,
                "level": 3,
                "above_levels_ids": "0,9999",
                "cohort_id": "3",
            },
        ]:
            Perimeter.objects.create(local_id=f"Local {perimeter['id']}", **perimeter)

    @staticmethod
    def fhir_care_sites():
        return {
            9999: care_site(9999, "All Hospitals", APHP, source_value="APHP"),
            2: care_site(2, "Hospital 1", GH, part_of=9999),
            3: care_site(3, "Hospital 2", GH, part_of=9999),
            4: care_site(4, "Service 1.1", HOPITAL, part_of=2),
            5: care_site(5, "Service 1.2", HOPITAL, part_of=2),
            6: care_site(6, "Service 2.1", HOPITAL, part_of=3),
            7: care_site(7, "Service 2.2", HOPITAL, part_of=3),
            8: care_site(8, "Service 1.1.1", POLE, part_of=4),
        }

    @staticmethod
    def fhir_lists():
        # 8 has no List yet
        return {cs_id: PerimeterList(cohort_id=f"L{cs_id}", cohort_size=str(cs_id * 10)) for cs_id in [9999, 2, 3, 4, 5, 6, 7]}

    def test_perimeters_created_from_existing_care_sites(self, mock_care_sites: MagicMock):
        mock_care_sites.return_value = self.fhir_care_sites()
        perimeters_data_model_objects_update()

        self.assertEqual(Perimeter.objects.all().count(), 8)
        deleted_perimeters = Perimeter.objects.exclude(delete_datetime__isnull=True).values_list("id", flat=True)
        self.assertEqual(sorted(deleted_perimeters), [0, 1])

        p8 = Perimeter.objects.get(id=8)
        self.assertEqual(p8.type_source_value, POLE)
        self.assertEqual(p8.source_value, "S8")
        self.assertEqual(p8.level, 4)
        self.assertEqual(p8.above_levels_ids, "9999,2,4")
        self.assertEqual(p8.full_path, "APHP-All Hospitals/S2-Hospital 1/S4-Service 1.1/S8-Service 1.1.1")
        self.assertIsNone(p8.cohort_id)
        self.assertIsNone(p8.cohort_size)
        p2 = Perimeter.objects.get(id=2)
        self.assertEqual(p2.cohort_id, "L2")
        self.assertEqual(p2.cohort_size, "20")
        self.assertEqual(p2.inferior_levels_ids, "4,5")
        self.assertEqual(Perimeter.objects.get(id=4).cohort_id, "L4")

    def test_cohort_change_alone_updates_the_perimeter(self, mock_care_sites: MagicMock):
        mock_care_sites.return_value = self.fhir_care_sites()
        perimeters_data_model_objects_update()
        lists = self.fhir_lists()
        lists[5] = PerimeterList(cohort_id="L5", cohort_size="999")
        self.mock_lists.side_effect = None
        self.mock_lists.return_value = lists
        mock_care_sites.return_value = self.fhir_care_sites()
        sync, _unchanged = compute_perimeters_sync()
        self.assertEqual([p.id for p in sync.to_update], [5])
        perimeters_data_model_objects_update()
        self.assertEqual(Perimeter.objects.get(id=5).cohort_size, "999")

    def test_root_without_list_aborts_without_changes(self, mock_care_sites: MagicMock):
        lists = self.fhir_lists()
        del lists[9999]
        self.mock_lists.side_effect = None
        self.mock_lists.return_value = lists
        mock_care_sites.return_value = self.fhir_care_sites()
        perimeters_data_model_objects_update()
        self.assertEqual(Perimeter.objects.all().count(), 5)
        self.assertEqual(Perimeter.objects.get(id=2).cohort_id, "2")

    def test_already_deleted_perimeter_keeps_its_delete_datetime(self, mock_care_sites: MagicMock):
        old_date = timezone.now() - timedelta(days=30)
        Perimeter.objects.all().filter(id=1).update(delete_datetime=old_date)
        mock_care_sites.return_value = self.fhir_care_sites()
        perimeters_data_model_objects_update()
        self.assertEqual(Perimeter.objects.all(even_deleted=True).get(id=1).delete_datetime, old_date)

    def test_deleted_perimeter_is_reactivated(self, mock_care_sites: MagicMock):
        Perimeter.objects.all().filter(id=2).update(delete_datetime=timezone.now())
        mock_care_sites.return_value = self.fhir_care_sites()
        sync, _unchanged = compute_perimeters_sync()
        self.assertEqual(sync.reactivated_ids, [2])
        perimeters_data_model_objects_update()
        self.assertIsNone(Perimeter.objects.get(id=2).delete_datetime)

    def test_only_changed_perimeters_are_updated(self, mock_care_sites: MagicMock):
        mock_care_sites.return_value = self.fhir_care_sites()
        perimeters_data_model_objects_update()
        mock_care_sites.return_value = self.fhir_care_sites()
        mock_care_sites.return_value[5].name = "Renamed"
        sync, unchanged = compute_perimeters_sync()
        self.assertEqual(sync.to_create, [])
        self.assertEqual(sync.to_delete_ids, [])
        # 5 and its parent's children list are unchanged, only 5's name/full_path changes
        self.assertEqual([p.id for p in sync.to_update], [5])
        self.assertEqual(len(unchanged), 7)

    def test_orphans_are_neither_created_nor_deleted(self, mock_care_sites: MagicMock):
        care_sites = self.fhir_care_sites()
        care_sites[0] = care_site(0, "P0", GH, part_of=404)
        care_sites[1] = care_site(1, "P1", GH, part_of=404)
        care_sites[10] = care_site(10, "New orphan", GH, part_of=404)
        mock_care_sites.return_value = care_sites
        perimeters_data_model_objects_update()
        self.assertFalse(Perimeter.objects.all(even_deleted=True).filter(id=10).exists())
        self.assertIsNone(Perimeter.objects.get(id=0).delete_datetime)
        self.assertIsNone(Perimeter.objects.get(id=1).delete_datetime)

    def test_missing_root_aborts_without_changes(self, mock_care_sites: MagicMock):
        care_sites = self.fhir_care_sites()
        del care_sites[9999]
        mock_care_sites.return_value = care_sites
        perimeters_data_model_objects_update()
        self.assertEqual(Perimeter.objects.all().count(), 5)

    def test_failure_rolls_back_all_writes(self, mock_care_sites: MagicMock):
        mock_care_sites.return_value = self.fhir_care_sites()
        with (
            mock.patch("accesses_fhir_perimeters.perimeters_updater.AccessesService.close_accesses", side_effect=RuntimeError("db error")),
            self.assertRaises(RuntimeError),
        ):
            perimeters_data_model_objects_update()
        self.assertEqual(Perimeter.objects.all().count(), 5)
        self.assertEqual(Perimeter.objects.get(id=2).name, "P2")
        self.assertIsNone(Perimeter.objects.get(id=0).delete_datetime)

    def test_compare_command_changes_nothing(self, mock_care_sites: MagicMock):
        mock_care_sites.return_value = self.fhir_care_sites()
        out = StringIO()
        with tempfile.NamedTemporaryFile(suffix=".json") as output:
            call_command("compare_fhir_perimeters", output=output.name, stdout=out)
            details = json.load(open(output.name))
        self.assertIn("À créer: 5", out.getvalue())
        self.assertEqual(details["to_delete_ids"], [0, 1])
        self.assertIn({"id": 2, "field": "name", "current": "P2", "fhir": "Hospital 1"}, details["field_diffs"])
        self.assertEqual(Perimeter.objects.all().count(), 5)
