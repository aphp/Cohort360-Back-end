import requests
from requests import Response, RequestException
from rest_framework import status

from exporters.apis.base import BaseAPI


class HadoopAPI(BaseAPI):
    conf_key = "HADOOP_API"

    def __init__(self):
        super().__init__()
        self.hive_db_path = self.api_conf.get('HIVE_DB_PATH')
        self.hive_user = self.api_conf.get('HIVE_USER')
        self.create_db_endpoint = self.api_conf.get('CREATE_DB_ENDPOINT')
        self.alter_db_endpoint = self.api_conf.get('ALTER_DB_ENDPOINT')

    def create_db(self, name: str, location: str) -> str:
        params = {"name": name,
                  "location": location,
                  "if_not_exists": True
                  }
        response = self.query_hadoop(endpoint=self.create_db_endpoint, params=params)
        return response.json().get('task_id')

    def change_db_ownership(self, location: str, db_user: str) -> None:
        params = {"location": location,
                  "uid": db_user,
                  "gid": "hdfs",
                  "recursive": True
                  }
        response = self.query_hadoop(endpoint=self.alter_db_endpoint, params=params)
        if not status.is_success(response.status_code):
            raise RequestException(response.text)
        response = response.json()
        if response.get('status') != "success" or response.get('ret_code') != 0:
            raise RequestException(f"Granting rights did not succeed: {response.get('err')}")

    def query_hadoop(self, endpoint: str, params: dict) -> Response:
        return requests.post(url=f"{self.url}{endpoint}",
                             params=params,
                             headers={'auth-token': self.auth_token})
