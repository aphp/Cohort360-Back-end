import os
from django.apps import AppConfig

env = os.environ


class AdminCohortConfig(AppConfig):
    name = 'admin_cohort'

    auth_hooks = env.get("USER_AUTHENTICATION_HOOKS")
    user_identity_hooks = env.get("USER_IDENTITY_HOOKS")

    HOOKS = {"USER_AUTHENTICATION": auth_hooks and  auth_hooks.split(",") or [],
             "USER_IDENTITY":  user_identity_hooks and  user_identity_hooks.split(",") or [],
             }
