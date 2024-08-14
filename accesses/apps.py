from django.apps import AppConfig


class AccessConfig(AppConfig):
    name = 'accesses'

    POST_AUTH_HOOKS = ["accesses.utils.impersonate_hook"]
