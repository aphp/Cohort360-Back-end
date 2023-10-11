from rest_framework_tracking.mixins import LoggingMixin


class RequestLogMixin(LoggingMixin):
    def handle_log(self):
        for f in ['query_params', 'data', 'errors', 'response']:
            self.log.pop(f, None)
        return super(RequestLogMixin, self).handle_log()
