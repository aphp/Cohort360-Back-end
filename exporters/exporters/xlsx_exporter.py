from exporters.exporters.csv_exporter import CSVExporter
from exporters.enums import ExportTypes


class XLSXExporter(CSVExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.XLSX.value
        self.target_location = self.export_api.export_xlsx_path
