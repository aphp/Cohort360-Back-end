from django.apps import AppConfig


class AccessConfig(AppConfig):
    name = 'accesses'

    def ready(self):
        from accesses import signals
        signals.onchange_allowed_users.connect(receiver=signals.manage_onchange_allowed_users,
                                               dispatch_uid=signals.manage_onchange_allowed_users.__name__)
