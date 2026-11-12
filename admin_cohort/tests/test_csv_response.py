import csv
import io

from django.test import SimpleTestCase

from admin_cohort.tools.csv_response import build_csv_response, neutralize_formula


class NeutralizeFormulaTest(SimpleTestCase):
    def test_cells_starting_with_a_formula_trigger_are_prefixed(self):
        for value in ("=1+1", "+33 1 23 45 67 89", "-Jane Doe", "@SUM(A1)", "\tvalue", "\rvalue"):
            self.assertEqual(neutralize_formula(value), f"'{value}", value)

    def test_other_cells_are_unchanged(self):
        for value in ("", "Project X", "1+1", "02/11/2026 12:00", "a=b"):
            self.assertEqual(neutralize_formula(value), value, value)


class BuildCsvResponseTest(SimpleTestCase):
    def setUp(self):
        self.response = build_csv_response(
            columns=["Name", "Comment"], rows=[["Jane", '=HYPERLINK("http://example.com")'], ["John", 'a;b "quoted"']], filename="file.csv"
        )

    def test_response_is_a_csv_attachment_that_must_not_be_cached(self):
        self.assertEqual(self.response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(self.response["Content-Disposition"], 'attachment; filename="file.csv"')
        self.assertEqual(self.response["Cache-Control"], "no-store")

    def test_content_starts_with_the_utf8_bom(self):
        self.assertTrue(self.response.content.startswith(b"\xef\xbb\xbf"))

    def test_content_is_delimited_by_semicolons_and_formulas_are_neutralized(self):
        rows = list(csv.reader(io.StringIO(self.response.content.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(rows, [["Name", "Comment"], ["Jane", '\'=HYPERLINK("http://example.com")'], ["John", 'a;b "quoted"']])
