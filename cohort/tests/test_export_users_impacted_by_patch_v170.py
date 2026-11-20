import csv
import io
import json
from smtplib import SMTPException
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError

from admin_cohort.tests.tests_tools import TestCaseWithDBs, new_random_user
from cohort.management.commands.export_users_impacted_by_patch_v170 import HEADER, filtre_impacte, impacte
from cohort.models import FhirFilter, Folder, Request, RequestQuerySnapshot

COMMAND = "export_users_impacted_by_patch_v170"


def serialized_query(criterion: dict, version: str = "v1.6.4") -> str:
    return json.dumps({"version": version, "_type": "request", "request": {"_type": "andGroup", "criteria": [criterion]}})


BIO_ENCOUNTER = {"resourceType": "Observation", "filterFhir": "code=123&encounter.status=finished"}
BIO_SANS_VISITE = {"resourceType": "Observation", "filterFhir": "code=123"}


class TestImpacteFunctions(TestCaseWithDBs):
    def test_filtre_impacte(self):
        self.assertTrue(filtre_impacte("code=1&encounter.status=finished"))
        self.assertTrue(filtre_impacte("encounter%2Eidentifier=123"))
        self.assertTrue(filtre_impacte("_filter=encounter.period-start%20gt%202020-01-01"))
        self.assertFalse(filtre_impacte("code=1&_filter=recorded-date%20gt%202020-01-01"))
        self.assertFalse(filtre_impacte(""))
        self.assertFalse(filtre_impacte(None))

    def test_impacte(self):
        self.assertTrue(impacte(BIO_ENCOUNTER))
        self.assertTrue(impacte({"resourceType": "Observation", "patientAge": {}}))
        self.assertFalse(impacte(BIO_SANS_VISITE))
        self.assertFalse(impacte({"resourceType": "Condition", "filterFhir": "encounter.status=finished"}))


class TestExportUsersImpactedByPatchV170(TestCaseWithDBs):
    def setUp(self):
        super().setUp()
        self.impacted_user = new_random_user()
        self.other_user = new_random_user()
        folder = Folder.objects.create(owner=self.impacted_user, name="f1")
        self.request = Request.objects.create(owner=self.impacted_user, name="r1", parent_folder=folder)
        RequestQuerySnapshot.objects.create(owner=self.impacted_user, request=self.request, serialized_query=serialized_query(BIO_ENCOUNTER))

        other_folder = Folder.objects.create(owner=self.other_user, name="f2")
        other_request = Request.objects.create(owner=self.other_user, name="r2", parent_folder=other_folder)
        # non impactés : sans critère de visite, déjà en v1.7.0, supprimé
        for query in [serialized_query(BIO_SANS_VISITE), serialized_query(BIO_ENCOUNTER, version="v1.7.0")]:
            RequestQuerySnapshot.objects.create(owner=self.other_user, request=other_request, serialized_query=query)
        # SafeDeleteModel.save() remet `deleted` à None : il faut passer par delete() (soft delete)
        RequestQuerySnapshot.objects.create(owner=self.other_user, request=other_request, serialized_query=serialized_query(BIO_ENCOUNTER)).delete()

    def read_attached_csv(self) -> list[list[str]]:
        _, content, mimetype = mail.outbox[0].attachments[0]
        self.assertEqual(mimetype, "text/csv")
        # Django décode les pièces jointes text/* en str : le BOM utf-8-sig devient "﻿"
        self.assertTrue(content.startswith("﻿"))
        return list(csv.reader(io.StringIO(content.removeprefix("﻿")), delimiter=";"))

    def test_send_csv_to_several_recipients(self):
        call_command(COMMAND, "--email", "a@aphp.fr", "b@aphp.fr", stdout=io.StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["a@aphp.fr", "b@aphp.fr"])
        rows = self.read_attached_csv()
        self.assertEqual(rows[0], HEADER)
        self.assertEqual([r[0] for r in rows[1:]], [self.impacted_user.username])
        self.assertEqual(rows[1][4], "1")  # nombre de requêtes impactées

    def test_impacted_filter_is_exported(self):
        FhirFilter.objects.create(
            fhir_resource="Observation",
            fhir_version="1.0.0",
            query_version="v1.6.4",
            name="bio",
            filter="encounter.status=finished",
            owner=self.other_user,
        )
        call_command(COMMAND, "--email", "a@aphp.fr", stdout=io.StringIO())
        rows = {r[0]: r for r in self.read_attached_csv()[1:]}
        self.assertEqual(set(rows), {self.impacted_user.username, self.other_user.username})
        self.assertEqual(rows[self.other_user.username][5], "1")  # nombre de filtres impactés

    def test_dry_run_sends_nothing(self):
        out = io.StringIO()
        call_command(COMMAND, "--dry-run", stdout=out)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("Utilisateurs exportés", out.getvalue())

    def test_email_required_without_dry_run(self):
        with self.assertRaises(CommandError):
            call_command(COMMAND, stdout=io.StringIO())
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_raises(self):
        with self.assertRaises(CommandError):
            call_command(COMMAND, "--email", "a@aphp.fr", "pas-un-email", stdout=io.StringIO())
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch("cohort.management.commands.export_users_impacted_by_patch_v170.EmailMessage.send")
    def test_smtp_failure_raises(self, mock_send):
        mock_send.side_effect = SMTPException()
        with self.assertRaises(CommandError):
            call_command(COMMAND, "--email", "a@aphp.fr", stdout=io.StringIO())
