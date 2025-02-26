import os

from django.apps import AppConfig

env = os.environ


class AccessConfig(AppConfig):
    name = 'accesses'

    FHIR_URL = env.get("FHIR_URL")
    FHIR_ACCESS_TOKEN = env.get("FHIR_ACCESS_TOKEN", "")

    POST_AUTH_HOOKS = ["accesses.utils.impersonate_hook"]
