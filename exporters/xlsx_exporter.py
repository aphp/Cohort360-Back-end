import os

from exporters.csv_exporter import CSVExporter
from exporters.enums import ExportTypes


class XLSXExporter(CSVExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.XLSX.value
        self.target_location = os.environ.get('EXPORT_CSV_PATH')
