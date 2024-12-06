import logging
from io import StringIO
from uuid import UUID

import requests
import yaml

from exporters.apis.base import BaseAPI


_logger = logging.getLogger('django.request')


class ExportAPI(BaseAPI):
    conf_key = "EXPORT_API"

    def __init__(self):
        super().__init__()
        self.required_table = "person"

    def launch_export(self, export_id: UUID, params: dict) -> str:
        try:
            yaml_data = yaml.dump(params, default_flow_style=False, sort_keys=False)
            yaml_file = StringIO(yaml_data)
        except yaml.YAMLError as e:
            _logger.error(f"Export[{export_id}] Error generating the yaml config from export params")
            raise e
        response = requests.post(url=f"{self.url}/yaml",
                                 files={"yaml_file": ("yaml_config.yaml", yaml_file, "application/x-yaml")},
                                 headers={'auth-token': self.auth_token})
        return response.json().get('task_id')
