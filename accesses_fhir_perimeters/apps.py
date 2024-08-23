import os

from django.apps import AppConfig

env = os.environ


class AccessesFhirAuxConfig(AppConfig):
    name = 'accesses_fhir_perimeters'
    FHIR_URL = env.get("FHIR_URL")
    ORGANIZATION_FILTER = env.get("ORGANIZATION_FILTER", "")
    FHIR_ACCESS_TOKEN = env.get("FHIR_ACCESS_TOKEN", "")
