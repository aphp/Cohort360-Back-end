import logging
import os
from pathlib import Path
from uuid import UUID

import requests
from rest_framework import status

from exporters.apis.base import BaseAPI
from exporters.utils import build_yaml

_logger = logging.getLogger('django.request')

EXPORT_YAML_FILE = Path(__file__).resolve().parent.parent / 'export-%s.yml'


class ExportAPI(BaseAPI):
    conf_key = "EXPORT_API"

    def __init__(self):
        super().__init__()
        self.required_table = "person"

    def launch_export(self, export_id: UUID, params: dict) -> str:
        file_path = str(EXPORT_YAML_FILE) % export_id
        _logger.info(f"Export [{export_id}] temporarily storing the yaml file at: {file_path}")
        file_saved = build_yaml(dict_in=params, outfile_path=file_path)
        if file_saved:
            response = requests.post(url=f"{self.url}/yaml",
                                     files={'yaml_file': open(file_path, 'rb')},
                                     headers={'auth-token': self.auth_token})
            if response.status_code == status.HTTP_200_OK:
                os.remove(file_path)
            return response.json().get('task_id')
        raise FileNotFoundError(f"Export [{export_id}] Error saving the yaml config file")
