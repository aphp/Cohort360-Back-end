from unittest import mock

from django.test import override_settings

from accesses import porthab
from accesses.porthab import (
    PorthabGrants,
    data_scopes_from_groups,
    fetch_porthab_grants,
    porthab_read_perimeter_ids,
    porthab_role,
    rights_from_groups,
)
from accesses.tests.base import AccessesAppTestsBase

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
