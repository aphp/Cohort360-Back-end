from unittest import mock

from django.test import override_settings
from rest_framework.exceptions import ValidationError

from accesses import porthab
from accesses.porthab import (
    PorthabGrants,
    data_scopes_from_groups,
    fetch_porthab_grants,
    porthab_read_perimeter_ids,
    porthab_role,
    rights_from_groups,
)
from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from accesses.services.perimeters import perimeters_service
from accesses.tests.base import AccessesAppTestsBase
from accesses.utils import impersonate_hook
from admin_cohort.auth.auth_backends import OIDCAuthBackend
from admin_cohort.models import User
from admin_cohort.services.auth import auth_service
from admin_cohort.tools.cache import construct_cache_key
from exports.services.rights_checker import rights_checker

PER = "/BBS_DA-N-EDS_DEV_PER_"


def with_grants(user, *codes, rights=()):
    return porthab.apply_grants(user, PorthabGrants(rights=frozenset(rights), data_scopes=frozenset(codes)))


@override_settings(PORTHAB_RIGHTS_ENABLED=True, PORTHAB_GROUP_PREFIX="EDS_DEV")
class PorthabDataScopesTests(AccessesAppTestsBase):
    def test_les_perimetres_sont_lus_dans_les_groupes(self):
        groups = [
            f"{PER}H_096_N",
            "BBS_DA-N-EDS_DEV_PER_APHP_P",
            f"{PER}UF_096012_X",
            "/BBS_DA-N-EDS_PER_H_096_N",
            "/BBS_DA-N-EDS_DEV_APP_COHORT_FULL_ADMIN",
            f"{PER}UC_096X421_N",
        ]
        assert data_scopes_from_groups(groups) == {"H_096_N", "APHP_P"}

    def test_les_codes_sont_resolus_en_perimetres(self):
        user = with_grants(self.user_y, "APHP_P", "GH_P0_N", "H_P3_P", "POLE_P11_N", "H_085_N")
        nomi, pseudo = porthab_read_perimeter_ids(user)
        assert nomi == {self.p0.id, self.p11.id}
        assert pseudo == {self.aphp.id, self.p3.id}

    def test_sans_perimetre_aucune_requete(self):
        with self.assertNumQueries(0):
            assert porthab_read_perimeter_ids(self.user_y) == (frozenset(), frozenset())

    def test_les_droits_de_donnees_sont_traduits(self):
        groups = [f"/BBS_DA-N-EDS_DEV_APP_COHORT_{slug}" for slug in ("SEARCH_IPP", "SEARCH_OPPOSED", "EXPORT_CSV", "EXPORT_JUPYTER")]
        assert rights_from_groups(groups) == {
            "right_search_patients_by_ipp",
            "right_search_opposed_patients",
            "right_export_csv_xlsx_nominative",
            "right_export_jupyter_nominative",
            "right_export_jupyter_pseudonymized",
        }

    def test_le_role_port_hab_ne_porte_que_la_gestion(self):
        role = porthab_role(with_grants(self.user_y, rights=("right_manage_users", "right_search_patients_by_ipp")))
        assert role.right_manage_users
        assert not role.right_search_patients_by_ipp

    @mock.patch("accesses.porthab.service_token", return_value="t")
    @mock.patch("accesses.porthab.requests.get")
    def test_l_endpoint_donne_droits_et_perimetres(self, get, _):
        get.return_value = mock.Mock(status_code=200, json=lambda: {"rights": ["cohort.full_admin", "cohort.export_csv"], "data_scopes": ["H_096_N"]})
        assert fetch_porthab_grants("7000001") == PorthabGrants(
            rights=frozenset({"right_full_admin", "right_export_csv_xlsx_nominative"}), data_scopes=frozenset({"H_096_N"})
        )

    @mock.patch("accesses.porthab.service_token", return_value="t")
    @mock.patch("accesses.porthab.requests.get")
    def test_un_endpoint_sans_perimetres_reste_lisible(self, get, _):
        get.return_value = mock.Mock(status_code=200, json=lambda: {"rights": []})
        assert fetch_porthab_grants("7000001").data_scopes == frozenset()


@override_settings(PORTHAB_RIGHTS_ENABLED=True, PORTHAB_GROUP_PREFIX="EDS_DEV")
class PorthabDataScopesAuthTests(AccessesAppTestsBase):
    def authenticate(self, claims):
        oidc = mock.Mock(**{"authenticate.return_value": claims["preferred_username"], "decode_token.return_value": claims})
        with mock.patch.dict(auth_service.authenticators, {"OIDC": oidc}):
            return auth_service.authenticate_request(token="t", auth_method="OIDC", headers={})

    def test_le_jeton_porte_les_perimetres(self):
        user, _ = self.authenticate({"preferred_username": self.user_y.username, "groups": [f"{PER}H_P3_N"]})
        assert user.porthab_data_scopes == {"H_P3_N"}

    def test_un_agent_avec_seulement_un_perimetre_est_cree_a_la_connexion(self):
        claims = {"preferred_username": "7000002", "given_name": "Alix", "family_name": "Durand", "groups": [f"{PER}H_P3_P"]}
        tokens = mock.Mock(access_token="t")
        with (
            mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.get_tokens", return_value=tokens),
            mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.decode_token", return_value=claims),
            mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.retrieve_username", return_value="7000002"),
        ):
            user = OIDCAuthBackend().authenticate(mock.Mock(), code="c")
        assert user == User.objects.get(username="7000002")

    @mock.patch("accesses.utils.fetch_porthab_grants")
    def test_l_impersonation_porte_les_perimetres_de_l_agent(self, fetch):
        fetch.return_value = PorthabGrants(rights=frozenset(), data_scopes=frozenset({"H_P3_N"}))
        admin = with_grants(self.user_y, rights=("right_full_admin",))
        assert impersonate_hook(admin, {"X-Impersonate": self.user_z.username}).porthab_data_scopes == {"H_P3_N"}

    def test_la_cle_de_cache_depend_des_perimetres(self):
        def key(user):
            request = mock.Mock(user=user, query_params={}, _request=mock.Mock(path="/x/"), spec=["user", "query_params", "_request"])
            return construct_cache_key(view_instance=self, view_method=self.test_la_cle_de_cache_depend_des_perimetres, request=request)

        assert key(with_grants(self.user_y, "H_P3_N")) != key(with_grants(self.user_y, "H_P3_P"))


@override_settings(PORTHAB_RIGHTS_ENABLED=True, PORTHAB_GROUP_PREFIX="EDS_DEV")
class PorthabDataReadingTests(AccessesAppTestsBase):
    def rights_by_perimeter(self, user, perimeters):
        return {dr.perimeter_id: dr for dr in accesses_service.get_data_reading_rights(user=user, target_perimeters_ids=[p.id for p in perimeters])}

    def test_un_agent_port_hab_seul_lit_ses_perimetres(self):
        user = with_grants(self.user_y, "H_P4_P", "POLE_P11_N")
        cibles = Perimeter.objects.filter(id__in=[self.p11.id, self.p12.id])
        assert accesses_service.user_has_data_reading_accesses_on_target_perimeters(user, cibles, read_mode="min")
        assert accesses_service.user_can_access_at_least_one_target_perimeter_in_nomi(user, cibles)
        assert not accesses_service.user_can_access_all_target_perimeters_in_nomi(user, cibles)
        assert not accesses_service.user_has_data_reading_accesses_on_target_perimeters(
            user, Perimeter.objects.filter(id=self.p3.id), read_mode="max"
        )

    def test_mes_droits_de_donnees_suivent_la_hierarchie(self):
        droits = self.rights_by_perimeter(with_grants(self.user_y, "H_P4_P", "POLE_P11_N"), [self.p11, self.p12])
        assert (droits[self.p11.id].right_read_patient_nominative, droits[self.p11.id].right_read_patient_pseudonymized) == (True, True)
        assert (droits[self.p12.id].right_read_patient_nominative, droits[self.p12.id].right_read_patient_pseudonymized) == (False, True)

    def test_union_avec_un_acces_natif(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_data_reader_nomi, perimeter=self.p3)
        user = with_grants(self.user_y, "H_P4_P")
        droits = self.rights_by_perimeter(user, [self.p3, self.p4])
        assert droits[self.p3.id].right_read_patient_nominative
        assert droits[self.p4.id].right_read_patient_pseudonymized and not droits[self.p4.id].right_read_patient_nominative

    def test_les_droits_globaux_port_hab_s_appliquent_aux_perimetres_lus(self):
        user = with_grants(self.user_y, "H_P4_N", rights=("right_search_patients_by_ipp", "right_export_csv_xlsx_nominative"))
        droit = self.rights_by_perimeter(user, [self.p4])[self.p4.id]
        assert droit.right_search_patients_by_ipp and droit.right_export_csv_xlsx_nominative
        assert not droit.right_export_jupyter_nominative

    def test_recherche_des_patients_opposes(self):
        assert not accesses_service.can_user_read_opposed_patient_data(with_grants(self.user_y, "H_P4_N"))
        assert accesses_service.can_user_read_opposed_patient_data(with_grants(self.user_z, rights=("right_search_opposed_patients",)))

    def test_droits_de_lecture_par_perimetre(self):
        user = with_grants(self.user_y, "H_P4_P", "POLE_P11_N", rights=("right_search_patients_by_ipp",))
        lectures = perimeters_service.get_data_read_rights_on_perimeters(
            user=user, is_request_filtered=False, filtered_perimeters=Perimeter.objects.all()
        )
        par_id = {lecture.perimeter.id: lecture for lecture in lectures}
        assert par_id[self.p4.id].right_read_patient_pseudonymized and not par_id[self.p4.id].right_read_patient_nominative
        assert par_id[self.p11.id].right_read_patient_nominative
        assert all(lecture.right_search_patients_by_ipp for lecture in lectures)

    def test_le_controle_d_export_csv(self):
        nomi = self.rights_by_perimeter(with_grants(self.user_y, "H_P4_N", rights=("right_export_csv_xlsx_nominative",)), [self.p4])
        rights_checker._check_rights(list(nomi.values()), "right_export_csv_xlsx_nominative")
        pseudo = self.rights_by_perimeter(with_grants(self.user_z, "H_P4_P", rights=("right_export_csv_xlsx_nominative",)), [self.p4])
        with self.assertRaises(ValidationError):
            rights_checker._check_rights(list(pseudo.values()), "right_read_patient_nominative")
