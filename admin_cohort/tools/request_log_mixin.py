import logging

from rest_framework_tracking.mixins import LoggingMixin

_logger = logging.getLogger("django.request")


class RequestLogMixin(LoggingMixin):
    def handle_log(self):
        for f in ['errors', 'response']:
            self.log.pop(f, None)
        return super(RequestLogMixin, self).handle_log()
