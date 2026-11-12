import csv
import io
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status

from accesses.models import Access, Profile, Role
from admin_cohort.tests.tests_tools import new_user_and_profile
from admin_cohort.types import JobStatus
from exports.enums import ExportPurpose
from exports.models import Export, ExportProjectDetails
from exports.services.export_purposes_extraction import COLUMNS, USERS_TIMEZONE
from exports.tests.base_test import ExportsTestBase
from exports.views import ExportViewSet

EXTRACTION_URL = "/exports/purposes-extraction/"


class ExportPurposesExtractionTest(ExportsTestBase):
    view_set = ExportViewSet

    def setUp(self):
        super().setUp()
        self.extraction_view = self.view_set.as_view({"get": "purposes_extraction"})
        self.extractor_role = Role.objects.create(name="PURPOSES EXTRACTOR", right_extract_export_purposes=True)
        self.extractor_user, extractor_profile = new_user_and_profile()
        self.create_access(profile=extractor_profile, role=self.extractor_role)

    def create_access(self, profile: Profile, role: Role) -> Access:
        return Access.objects.create(
            profile=profile,
            perimeter=self.perimeter_aphp,
            role=role,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timedelta(days=365),
        )

    def create_export(self, created_on: date, at=time(12), output_format="csv", purpose=None, job_status=JobStatus.finished) -> Export:
        export = Export.objects.create(owner=self.exporter_user, output_format=output_format, purpose=purpose, request_job_status=job_status)
        # created_at is set automatically on creation. Given in Paris time, as read by the users
        Export.objects.filter(pk=export.pk).update(created_at=datetime.combine(created_on, at, tzinfo=USERS_TIMEZONE))
        export.refresh_from_db()
        return export

    def extract(self, query: str, request_user=None):
        request = self.make_request(url=f"{EXTRACTION_URL}?{query}", http_verb="get", request_user=request_user or self.extractor_user)
        return self.extraction_view(request)

    @staticmethod
    def read_rows(response):
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
        return [dict(zip(COLUMNS, row)) for row in rows[1:]]

    def test_extraction_is_forbidden_without_the_right(self):
        self.create_export(created_on=date(2026, 11, 2))
        response = self.extract(query="output_format=csv", request_user=self.user_without_rights)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_full_admin_can_extract(self):
        self.create_export(created_on=date(2026, 11, 2))
        response = self.extract(query="output_format=csv", request_user=self.admin_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_extraction_returns_a_safe_csv_file_with_the_expected_columns(self):
        export = self.create_export(created_on=date(2026, 11, 2), purpose=ExportPurpose.INTERNAL_RESEARCH.value)
        title = '=HYPERLINK("http://example.com")'
        ExportProjectDetails.objects.create(export=export, title=title, project_leader="Jane Doe")
        response = self.extract(query="output_format=csv")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers["content-type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        header = next(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(header, COLUMNS)
        rows = self.read_rows(response)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Titre du projet"], "'" + title)

    def test_extraction_only_contains_the_requested_output_formats(self):
        self.create_export(created_on=date(2026, 11, 2), output_format="csv")
        self.create_export(created_on=date(2026, 11, 2), output_format="xlsx")
        self.create_export(created_on=date(2026, 11, 2), output_format="hive")
        rows = self.read_rows(self.extract(query="output_format=xlsx"))
        self.assertEqual([row["Type d'export"] for row in rows], ["XLSX"])
        rows = self.read_rows(self.extract(query="output_format=csv,xlsx"))
        self.assertEqual(sorted(row["Type d'export"] for row in rows), ["CSV", "XLSX"])

    def test_extraction_rejects_invalid_output_formats(self):
        for query in ("output_format=", "output_format=hive", "output_format=csv,hive", ""):
            response = self.extract(query=query)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, query)

    def test_extraction_rejects_an_end_date_earlier_than_the_start_date(self):
        response = self.extract(query="output_format=csv&start_date=2026-11-10&end_date=2026-11-09")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_bounds_are_inclusive_days_in_paris_time(self):
        # 00:30 in Paris is still the previous day in UTC, on both bounds
        self.create_export(created_on=date(2026, 10, 31), at=time(23, 59))
        self.create_export(created_on=date(2026, 11, 1), at=time(0, 30))
        self.create_export(created_on=date(2026, 11, 30), at=time(23, 30))
        self.create_export(created_on=date(2026, 12, 1), at=time(0, 30))
        rows = self.read_rows(self.extract(query="output_format=csv&start_date=2026-11-01&end_date=2026-11-30"))
        self.assertEqual([row["Date et heure de l'export"] for row in rows], ["01/11/2026 00:30", "30/11/2026 23:30"])

    def test_extraction_without_dates_contains_all_exports(self):
        for day in (date(2025, 1, 1), date(2026, 11, 1)):
            self.create_export(created_on=day)
        rows = self.read_rows(self.extract(query="output_format=csv"))
        self.assertEqual(len(rows), 2)

    def test_extraction_returns_no_content_when_no_export_matches(self):
        self.create_export(created_on=date(2026, 11, 2))
        response = self.extract(query="output_format=csv&start_date=2026-12-01")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_extraction_row_content(self):
        research_export = self.create_export(created_on=date(2026, 11, 2), purpose=ExportPurpose.INTERNAL_RESEARCH.value)
        ExportProjectDetails.objects.create(
            export=research_export, title="Project X", project_leader="Jane Doe", start_date=date(2026, 1, 15), end_date=None
        )
        self.create_export(created_on=date(2026, 11, 3), purpose=ExportPurpose.CARE_SUPPORT.value, job_status=JobStatus.failed)
        self.create_export(created_on=date(2026, 11, 4))

        research_row, care_row, old_row = self.read_rows(self.extract(query="output_format=csv"))

        self.assertEqual(research_row["APH"], self.exporter_user.username)
        self.assertEqual(research_row["Profil"], self.csv_exporter_role.name)
        self.assertEqual(research_row["Périmètre"], self.perimeter_aphp.name)
        self.assertEqual(research_row["Date et heure de l'export"], "02/11/2026 12:00")
        self.assertEqual(research_row["Type d'export"], "CSV")
        self.assertEqual(research_row["Statut"], "Terminé")
        self.assertEqual(research_row["Motivation"], "Recherche interne")
        self.assertEqual(research_row["Titre du projet"], "Project X")
        self.assertEqual(research_row["Porteur du projet"], "Jane Doe")
        self.assertEqual(research_row["Date de début du projet"], "15/01/2026")
        self.assertEqual(research_row["Date de fin du projet"], "")

        self.assertEqual(care_row["Statut"], "Erreur")
        self.assertEqual(care_row["Motivation"], "Appui au soin")
        self.assertEqual(care_row["Titre du projet"], "")

        # Export made before the purpose was collected
        self.assertEqual(old_row["Motivation"], "")
        self.assertEqual(old_row["Titre du projet"], "")

    def test_profiles_and_perimeters_are_listed_once_and_in_the_same_order(self):
        # The same access given through a second profile, and another role on the same perimeter
        orbis_profile = Profile.objects.create(user=self.exporter_user, source=settings.ACCESS_SOURCES[1], is_active=True)
        self.create_access(profile=orbis_profile, role=self.csv_exporter_role)
        self.create_access(profile=orbis_profile, role=self.datalab_reader_role)
        self.create_export(created_on=date(2026, 11, 2))
        (row,) = self.read_rows(self.extract(query="output_format=csv"))
        self.assertEqual(row["Profil"], f"{self.csv_exporter_role.name} | {self.datalab_reader_role.name}")
        self.assertEqual(row["Périmètre"], f"{self.perimeter_aphp.name} | {self.perimeter_aphp.name}")
