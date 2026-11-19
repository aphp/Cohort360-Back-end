from unittest import mock

from django.http import Http404
from django.test import override_settings

from accesses.models import Perimeter
from accesses.porthab import PorthabGrants, apply_grants
from datetime import timedelta

from django.utils import timezone

from accesses.models import Access, Role
from accesses.tests.base import data_reader_nomi_role_definition
from admin_cohort.tests.tests_tools import new_random_user, new_user_and_profile, TestCaseWithDBs
from cohort.models import Folder, Request, RequestQuerySnapshot, CohortResult, DatedMeasure
from cohort.services.cohort_rights import (
    EXPORT_CSV_XLSX_NOMI,
    EXPORT_JUPYTER_PSEUDO,
    READ_PATIENT_NOMI,
    READ_PATIENT_PSEUDO,
    CohortRightsService,
)

SHARED_GROUP_ID = "9000001"
OTHER_GROUP_ID = "9000002"


class TestCohortRightsService(TestCaseWithDBs):
    def setUp(self):
        super().setUp()
        self.user1 = new_random_user()
        self.user2 = new_random_user()
        Perimeter.objects.create(id=1, name="P1", local_id="p1", cohort_id="101")
        Perimeter.objects.create(id=2, name="P2", local_id="p2", cohort_id="102")
        self.create_cohort(owner=self.user1, group_id=SHARED_GROUP_ID, perimeters_ids=["101"])
        self.create_cohort(owner=self.user2, group_id=SHARED_GROUP_ID, perimeters_ids=["102"])
        self.cohort_rights_service = CohortRightsService()

    @staticmethod
    def create_cohort(owner, group_id, perimeters_ids):
        folder = Folder.objects.create(owner=owner, name="f1")
        request = Request.objects.create(owner=owner, name="Request 1", description="Request 1", parent_folder=folder)
        rqs = RequestQuerySnapshot.objects.create(owner=owner, request=request, serialized_query="{}", perimeters_ids=perimeters_ids)
        dm = DatedMeasure.objects.create(owner=owner, request_query_snapshot=rqs)
        return CohortResult.objects.create(owner=owner, request_query_snapshot=rqs, dated_measure=dm, group_id=group_id)

    def test_get_cohort_perimeters_with_group_id_shared_by_two_owners(self):
        perimeters = self.cohort_rights_service.get_cohort_perimeters(cohorts_ids=[SHARED_GROUP_ID], owner=self.user1)
        self.assertEqual(list(perimeters), [SHARED_GROUP_ID])
        self.assertEqual([p.cohort_id for p in perimeters[SHARED_GROUP_ID]], ["101"])

    def test_get_cohort_perimeters_uses_the_cohort_of_the_requesting_owner(self):
        perimeters = self.cohort_rights_service.get_cohort_perimeters(cohorts_ids=[SHARED_GROUP_ID], owner=self.user2)
        self.assertEqual([p.cohort_id for p in perimeters[SHARED_GROUP_ID]], ["102"])

    def test_get_cohort_perimeters_ignores_and_logs_cohorts_of_other_owners(self):
        self.create_cohort(owner=self.user2, group_id=OTHER_GROUP_ID, perimeters_ids=["102"])
        with self.assertLogs("cohort.services.cohort_rights", level="WARNING") as logs:
            perimeters = self.cohort_rights_service.get_cohort_perimeters(cohorts_ids=[SHARED_GROUP_ID, OTHER_GROUP_ID], owner=self.user1)
        self.assertEqual(list(perimeters), [SHARED_GROUP_ID])
        self.assertIn(OTHER_GROUP_ID, logs.output[0])

    def test_get_cohort_perimeters_raises_404_when_no_cohort_belongs_to_owner(self):
        self.create_cohort(owner=self.user2, group_id=OTHER_GROUP_ID, perimeters_ids=["102"])
        with self.assertRaises(Http404):
            self.cohort_rights_service.get_cohort_perimeters(cohorts_ids=[OTHER_GROUP_ID], owner=self.user1)

    def test_retrieve_virtual_cohorts_ids_from_snapshot_filters_on_owner_only_when_given(self):
        self.create_cohort(owner=self.user2, group_id=OTHER_GROUP_ID, perimeters_ids=["102"])
        cohorts_ids = [SHARED_GROUP_ID, OTHER_GROUP_ID]
        all_owners = self.cohort_rights_service.retrieve_virtual_cohorts_ids_from_snapshot(cohorts_ids=cohorts_ids)
        user1_only = self.cohort_rights_service.retrieve_virtual_cohorts_ids_from_snapshot(cohorts_ids=cohorts_ids, owner=self.user1)
        self.assertEqual(sorted(all_owners), sorted(cohorts_ids))
        self.assertEqual(user1_only, {SHARED_GROUP_ID: ["101"]})

    def test_retrieve_virtual_cohorts_ids_from_snapshot_does_not_merge_owners_when_owner_not_given(self):
        result = self.cohort_rights_service.retrieve_virtual_cohorts_ids_from_snapshot(cohorts_ids=[SHARED_GROUP_ID])
        self.assertIn(result[SHARED_GROUP_ID], (["101"], ["102"]))

    def test_get_cohort_perimeters_merges_cohorts_with_group_id_duplicated_for_same_owner(self):
        self.create_cohort(owner=self.user1, group_id=SHARED_GROUP_ID, perimeters_ids=["101", "102"])
        perimeters = self.cohort_rights_service.get_cohort_perimeters(cohorts_ids=[SHARED_GROUP_ID], owner=self.user1)
        self.assertEqual(sorted(p.cohort_id for p in perimeters[SHARED_GROUP_ID]), ["101", "102"])

    @mock.patch.object(CohortRightsService, "get_rights_on_perimeters")
    @mock.patch.object(CohortRightsService, "get_perimeter_ids_per_right")
    @mock.patch("cohort.services.cohort_rights.accesses_service.get_user_valid_accesses")
    def test_get_user_rights_on_cohorts_with_group_id_shared_by_two_owners(
        self, mock_valid_accesses, mock_accesses_per_right, mock_rights_on_perimeters
    ):
        mock_valid_accesses.return_value = ["access"]
        mock_accesses_per_right.return_value = {}
        mock_rights_on_perimeters.return_value = {READ_PATIENT_NOMI: True}
        rights = self.cohort_rights_service.get_user_rights_on_cohorts(group_ids=SHARED_GROUP_ID, user=self.user1)
        self.assertEqual(rights, [{"cohort_id": SHARED_GROUP_ID, "rights": {READ_PATIENT_NOMI: True}}])


@override_settings(PORTHAB_RIGHTS_ENABLED=True, PORTHAB_GROUP_PREFIX="EDS_DEV")
class TestCohortRightsWithPorthab(TestCaseWithDBs):
    def setUp(self):
        super().setUp()
        self.user = new_random_user()
        Perimeter.objects.create(id=1, name="H1", local_id="h1", cohort_id="101", source_value="001", type_source_value="Hôpital")
        Perimeter.objects.create(id=2, name="H2", local_id="h2", cohort_id="102", source_value="002", type_source_value="Hôpital")
        TestCohortRightsService.create_cohort(owner=self.user, group_id=SHARED_GROUP_ID, perimeters_ids=["101"])
        TestCohortRightsService.create_cohort(owner=self.user, group_id=OTHER_GROUP_ID, perimeters_ids=["102"])

    def rights(self, *codes, rights=()):
        apply_grants(self.user, PorthabGrants(rights=frozenset(rights), data_scopes=frozenset(codes)))
        resultat = CohortRightsService().get_user_rights_on_cohorts(group_ids=f"{SHARED_GROUP_ID},{OTHER_GROUP_ID}", user=self.user)
        return {item["cohort_id"]: item["rights"] for item in resultat}

    def test_un_agent_port_hab_seul_a_ses_droits_sur_ses_cohortes(self):
        droits = self.rights("H_001_N", "H_002_P", rights=("right_export_csv_xlsx_nominative",))
        assert droits[SHARED_GROUP_ID][READ_PATIENT_NOMI] and droits[SHARED_GROUP_ID][EXPORT_CSV_XLSX_NOMI]
        assert droits[OTHER_GROUP_ID][READ_PATIENT_PSEUDO]
        assert not droits[OTHER_GROUP_ID][READ_PATIENT_NOMI]
        assert not droits[OTHER_GROUP_ID][EXPORT_CSV_XLSX_NOMI]

    def test_un_perimetre_nominatif_ne_donne_pas_la_lecture_pseudonymisee(self):
        droits = self.rights("H_001_N", rights=("right_export_jupyter_pseudonymized",))
        assert droits[SHARED_GROUP_ID][READ_PATIENT_NOMI]
        assert not droits[SHARED_GROUP_ID][READ_PATIENT_PSEUDO]
        assert not droits[SHARED_GROUP_ID][EXPORT_JUPYTER_PSEUDO]

    def test_l_export_port_hab_s_applique_aussi_aux_perimetres_natifs(self):
        _, profile = new_user_and_profile()
        self.user = profile.user
        Access.objects.create(
            profile=profile,
            role=Role.objects.create(**data_reader_nomi_role_definition),
            perimeter=Perimeter.objects.get(id=2),
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timedelta(days=1),
        )
        TestCohortRightsService.create_cohort(owner=self.user, group_id=SHARED_GROUP_ID, perimeters_ids=["101"])
        TestCohortRightsService.create_cohort(owner=self.user, group_id=OTHER_GROUP_ID, perimeters_ids=["102"])
        droits = self.rights("H_001_N", rights=("right_export_csv_xlsx_nominative",))
        assert droits[OTHER_GROUP_ID][READ_PATIENT_NOMI] and droits[OTHER_GROUP_ID][EXPORT_CSV_XLSX_NOMI]

    def test_sans_acces_ni_perimetre_port_hab_toujours_404(self):
        with self.assertRaises(Http404):
            self.rights()
