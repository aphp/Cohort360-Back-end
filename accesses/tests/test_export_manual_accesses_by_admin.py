import csv
import os
import tempfile
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from accesses.management.commands import export_manual_accesses_by_admin
from accesses.models import Access, Perimeter, Profile, Role
from admin_cohort.models import User
from admin_cohort.tests.tests_tools import TestCaseWithDBs


class ExportManualAccessesByAdminTest(TestCaseWithDBs):
    def setUp(self):
        now = timezone.now()
        self.admin = User.objects.create(username="1000000", firstname="Admin", lastname="NAMIK", email="admin@aphp.fr")
        self.other = User.objects.create(username="2000000", firstname="Other", lastname="ADMIN", email="other@aphp.fr")
        self.perimeter = Perimeter.objects.create(id=1, local_id="1", name="Hôpital A", level=1)
        self.role = Role.objects.create(name="Lecteur")

        def make_user(username, lastname, **kwargs):
            return User.objects.create(username=username, firstname="Jean", lastname=lastname, email=f"{username}@aphp.fr", **kwargs)

        def grant(user, by, end, source="Manual", updated_by=None, is_active=True):
            profile, _ = Profile.objects.get_or_create(user=user, source=source, defaults={"is_active": is_active})
            return Access.objects.create(
                profile=profile,
                perimeter=self.perimeter,
                role=self.role,
                source=source,
                start_datetime=now - timedelta(days=10),
                end_datetime=end,
                created_by=by,
                updated_by=updated_by or by,
            )

        future = now + timedelta(days=30)
        past = now - timedelta(days=1)
        # created by admin, with one access by admin and one by someone else
        self.created = make_user("3000001", "ALPHA", created_by=self.admin, updated_by=self.admin)
        grant(self.created, self.admin, future)
        grant(self.created, self.other, future)
        # created before 3.29.1 (no created_by), only matched through its access
        self.via_access = make_user("3000002", "BRAVO")
        grant(self.via_access, self.admin, future)
        # admin only closed its access: matched, but no current access left
        self.closed = make_user("3000003", "CHARLIE")
        grant(self.closed, self.other, past, updated_by=self.admin)
        # not related to admin
        self.unrelated = make_user("3000004", "DELTA", created_by=self.other)
        grant(self.unrelated, self.other, future)
        # created by admin but no Manual profile: excluded
        self.orbis = make_user("3000005", "ECHO", created_by=self.admin)
        grant(self.orbis, self.admin, future, source="ORBIS")
        make_user("3000006", "FOXTROT", created_by=self.admin)
        # inactive Manual profile: matched, but its access is not current
        self.inactive = make_user("3000007", "GOLF")
        grant(self.inactive, self.admin, future, is_active=False)

    def run_command(self, *args):
        out, err = StringIO(), StringIO()
        call_command(export_manual_accesses_by_admin.Command(), *args, stdout=out, stderr=err)
        return list(csv.reader(StringIO(out.getvalue()), delimiter=";")), err.getvalue()

    def test_unknown_admin(self):
        with self.assertRaisesMessage(CommandError, "Utilisateur introuvable : 9999999"):
            self.run_command("--username", "9999999")

    def test_export_rows(self):
        rows, err = self.run_command("--username", "1000000")
        self.assertEqual(rows[0], export_manual_accesses_by_admin.HEADERS)
        body = rows[1:]
        self.assertEqual([r[0] for r in body], ["3000001", "3000001", "3000002", "3000003", "3000007"])
        self.assertEqual(len(rows[0]), 11)
        self.assertEqual(sorted(r[10] for r in body[:2]), ["Non", "Oui"])
        self.assertEqual(body[0][4], str(self.admin))
        self.assertEqual(body[2][4], "")
        self.assertEqual(body[2][6:], ["Hôpital A", "Lecteur", body[2][8], body[2][9], "Oui"])
        self.assertEqual(body[3][6:], [""] * 5)
        self.assertEqual(body[4][6:], [""] * 5)
        self.assertIn("4 compte(s), 5 ligne(s)", err)

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "export.csv")
            self.run_command("--username", "1000000", "--output", path)
            with open(path, encoding="utf-8") as f:
                content = f.read()
        self.assertTrue(content.startswith("﻿Identifiant APH;"))
        self.assertEqual(len(content.strip().splitlines()), 6)
