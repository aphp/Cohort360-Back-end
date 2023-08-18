import importlib

from django.apps import AppConfig


class AccessConfig(AppConfig):
    name = 'accesses'

    def ready(self):
        importlib.import_module("accesses.signals")
