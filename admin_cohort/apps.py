from django.apps import AppConfig


class AdminCohortConfig(AppConfig):
    name = 'admin_cohort'

    HOOKS = {"USER_AUTHENTICATION": ["admin_cohort.tools.hooks.authenticate_user"],
             "USER_IDENTITY": ["admin_cohort.tools.hooks.check_user_identity"],
             }
