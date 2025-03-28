import os

from django.apps import AppConfig

env = os.environ


class AccessConfig(AppConfig):
    name = 'accesses'

    FHIR_URL = env.get("FHIR_URL")
    POST_AUTH_HOOKS = ["accesses.utils.impersonate_hook"]
