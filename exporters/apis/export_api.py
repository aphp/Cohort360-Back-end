import logging
import os
from pathlib import Path

import requests

from exporters.apis.base import BaseAPI
from exporters.utils import build_yaml
from exports.models import Export

_logger = logging.getLogger('django.request')

EXPORT_YAML_FILE = Path(__file__).resolve().parent.parent / 'export-yaml-%s.yml'


class ExportAPI(BaseAPI):
    conf_key = "EXPORT_API"

    def __init__(self):
        super().__init__()
        self.required_table = "person"

    def launch_export(self, params: dict) -> str:
        export_id = params.pop("export_id")
        file_path = str(EXPORT_YAML_FILE) % export_id
        build_yaml(dict_in=params, outfile_path=file_path)
        self.persist_yaml_payload(export_id=export_id, file_path=file_path)
        response = requests.post(url=f"{self.url}/yaml",
                                 files={'yaml_file': open(file_path, 'rb')},
                                 headers={'auth-token': self.auth_token})
        return response.json().get('task_id')

    @staticmethod
    def persist_yaml_payload(export_id: str, file_path: str):
        export = Export.objects.get(pk=export_id)
        with open(file_path, 'rb') as f:
            export.yaml_payload = f.read()
            export.save()
        os.remove(file_path)
