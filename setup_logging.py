# https://docs.python.org/3.11/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network
# https://docs.python.org/3.11/howto/logging-cookbook.html#running-a-logging-socket-listener-in-production
import json
import logging
import socketserver
import struct
import sys
from logging.handlers import RotatingFileHandler, DEFAULT_TCP_LOGGING_PORT
from pathlib import Path

BUILTIN_WARNINGS_LOGGER_NAME = 'py.warnings'
INFO_LOGGER_NAME = 'info'

BASE_DIR = Path(__file__).resolve().parent


class CustomRotatingFileHandler(RotatingFileHandler):

    def __init__(self, name, *args, **kwargs):
        super(CustomRotatingFileHandler, self).__init__(*args, **kwargs)
        self.name = name

    def handle(self, record):
        if record.name == BUILTIN_WARNINGS_LOGGER_NAME:
            record.name = INFO_LOGGER_NAME
        if record.name == self.name:
            return super(CustomRotatingFileHandler, self).handle(record)
        pass


def configure_handlers() -> [logging.Handler]:
    rotation_basis = dict(backupCount=1000, maxBytes=100 * 1024 * 1024)

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    dj_info_handler = CustomRotatingFileHandler(name='info', filename=BASE_DIR / "log/django.log", **rotation_basis)
    dj_error_handler = CustomRotatingFileHandler(name='django.request', filename=BASE_DIR / "log/django.error.log", **rotation_basis)
    guni_error_handler = CustomRotatingFileHandler(name='gunicorn.error', filename=BASE_DIR / "log/gunicorn.error.log", **rotation_basis)
    guni_access_handler = CustomRotatingFileHandler(name='gunicorn.access', filename=BASE_DIR / "log/gunicorn.access.log", **rotation_basis)

    return [stream_handler,
            dj_info_handler,
            dj_error_handler,
            guni_error_handler,
            guni_access_handler]


def handle_log_record(record):
    logger = logging.getLogger('root')
    logger.handle(record)


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    def handle(self):
        """ Handle multiple requests - each expected to be a 4-byte length,
            followed by the LogRecord in pickle format. Logs the record
            according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = json.loads(chunk)
            record = logging.makeLogRecord(obj)
            handle_log_record(record)


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, host='localhost', port=DEFAULT_TCP_LOGGING_PORT, handler=LogRecordStreamHandler):
        super(LogRecordSocketReceiver, self).__init__(server_address=(host, port), RequestHandlerClass=handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()], [], [], self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort


def main():
    fmt = "%(levelname)s %(asctime)s <%(name)s> pid=%(process)d module=%(filename)s msg=`%(message)s`"
    logging.basicConfig(level=logging.INFO,
                        format=fmt,
                        handlers=configure_handlers())
    tcp_server = LogRecordSocketReceiver()
    tcp_server.serve_until_stopped()


if __name__ == '__main__':
    main()