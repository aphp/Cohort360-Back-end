import csv
import io
from typing import Iterable, List

from django.http import HttpResponse

# French Excel expects `;` as delimiter
CSV_DELIMITER = ";"
# A cell starting with one of these characters is interpreted as a formula by spreadsheet software (CSV injection)
FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def neutralize_formula(value: str) -> str:
    """Prefix a cell that could be read as a formula, so that it is displayed as plain text"""
    return f"'{value}" if value.startswith(FORMULA_TRIGGERS) else value


def build_csv_response(columns: List[str], rows: Iterable[List[str]], filename: str) -> HttpResponse:
    """
    Build a CSV file response meant to be opened with a spreadsheet software.
    Such files usually hold personal data: cells are protected against formula injection
    and the response must not be kept by browsers or proxies.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=CSV_DELIMITER)
    writer.writerow(columns)
    writer.writerows([neutralize_formula(value) for value in row] for row in rows)
    # utf-8-sig adds the BOM that Excel needs to read the file as UTF-8
    response = HttpResponse(buffer.getvalue().encode("utf-8-sig"), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response
