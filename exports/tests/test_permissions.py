from rest_framework.exceptions import PermissionDenied

from exports.permissions import check_allow_nomi_export, check_allow_pseudo_export
from exports.tests.base_test import ExportsTestBase


class PermissionsTestCase(ExportsTestBase):
    def test_pseudo_csv_export_is_always_forbidden(self):
        with self.assertRaises(PermissionDenied):
            check_allow_pseudo_export(self.exporter_user, "csv")

    def test_pseudo_xlsx_export_is_always_forbidden(self):
        with self.assertRaises(PermissionDenied):
            check_allow_pseudo_export(self.exporter_user, "xlsx")

    def test_nomi_csv_export_requires_right(self):
        with self.assertRaises(PermissionDenied):
            check_allow_nomi_export(self.user_without_rights, "csv")

    def test_nomi_csv_export_allowed_with_right(self):
        self.assertTrue(check_allow_nomi_export(self.exporter_user, "csv"))
