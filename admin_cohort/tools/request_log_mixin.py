import logging

from django.utils.timezone import now
from rest_framework import status
from rest_framework_tracking.mixins import LoggingMixin

_logger = logging.getLogger("django.request")


class RequestLogMixin(LoggingMixin):
    def handle_log(self):
        for f in ['query_params', 'data', 'errors', 'response']:
            self.log.pop(f, None)
        return super(RequestLogMixin, self).handle_log()


class JWTLoginRequestLogMixin(RequestLogMixin):

    initial = {}

    def __init__(self, *args, **kwargs):
        super(JWTLoginRequestLogMixin, self).__init__(*args, **kwargs)
        self.log = {}

    def init_request_log(self, request):
        if self.should_log(request=request, response=None):
            self.log["requested_at"] = now()

    def finalize_request_log(self, request):
        if self.should_log(request=request, response=None):
            self.log.update({"remote_addr": self._get_ip_address(request),
                             "view": self._get_view_name(request),
                             "view_method": self._get_view_method(request),
                             "path": self._get_path(request),
                             "host": request.get_host(),
                             "method": request.method,
                             "user": self._get_user(request),
                             "username_persistent": self._get_user(request).get_username() if self._get_user(request) else "Anonymous",
                             "response_ms": self._get_response_ms(),
                             "status_code": status.HTTP_200_OK})
            try:
                self.handle_log()
            except Exception as e:
                _logger.exception("Logging API call raise exception!", exc_info=e)
