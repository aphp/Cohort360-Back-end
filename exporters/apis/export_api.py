import logging
from io import BytesIO
from typing import Union
from uuid import UUID

import requests
import yaml
from django.http import JsonResponse
from rest_framework import status

from exporters.apis.base import BaseAPI


logger = logging.getLogger(__name__)


class ExportAPI(BaseAPI):
    conf_key = "EXPORT_API"

    def __init__(self):
        super().__init__()
        self.required_table = "person"
        self.export_csv_path = self.api_conf.get('EXPORT_CSV_PATH')
        self.export_xlsx_path = self.api_conf.get('EXPORT_XLSX_PATH')
        self.disable_data_translation = self.api_conf.get('DISABLE_DATA_TRANSLATION')

    def launch_export(self, export_id: UUID, params: dict) -> Union[str, JsonResponse]:
        try:
            yaml_data = yaml.dump(params, default_flow_style=False, sort_keys=False)
            yaml_file = BytesIO(yaml_data.encode("utf-8"))
        except yaml.YAMLError as e:
            logger.error(f"Export[{export_id}] Error generating the yaml config from export params")
            raise e
        response = requests.post(url=f"{self.url}/yaml",
                                 files={"yaml_file": ("yaml_file.yaml", yaml_file, "application/x-yaml")},
                                 headers={'auth-token': self.auth_token})
        if response.status_code == status.HTTP_200_OK:
            return response.json().get('task_id')
        logger.error(f"Export[{export_id}] Error launching export: {response.json()}")
        return JsonResponse(data=response.json(), status=response.status_code)
