# https://docs.python.org/3.11/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network
# https://docs.python.org/3.11/howto/logging-cookbook.html#running-a-logging-socket-listener-in-production
import json
import logging
import socketserver
import struct
from logging.handlers import DEFAULT_TCP_LOGGING_PORT
from pathlib import Path

from pythonjsonlogger.jsonlogger import JsonFormatter

BUILTIN_WARNINGS_LOGGER_NAME = 'py.warnings'
INFO_LOGGER_NAME = 'info'

BASE_DIR = Path(__file__).resolve().parent


class CustomFileHandler(logging.FileHandler):

    def __init__(self, name, *args, **kwargs):
        super(CustomFileHandler, self).__init__(*args, **kwargs)
        self.name = name

    def handle(self, record):
        if record.name == BUILTIN_WARNINGS_LOGGER_NAME:
            record.name = INFO_LOGGER_NAME
        if record.name == self.name:
            return super(CustomFileHandler, self).handle(record)
        pass


def configure_handlers() -> [logging.Handler]:
    dj_info_handler = CustomFileHandler(name='info', filename=BASE_DIR / "log/django.log")
    dj_error_handler = CustomFileHandler(name='django.request', filename=BASE_DIR / "log/django.error.log")
    guni_error_handler = CustomFileHandler(name='gunicorn.error', filename=BASE_DIR / "log/gunicorn.error.log")
    guni_access_handler = CustomFileHandler(name='gunicorn.access', filename=BASE_DIR / "log/gunicorn.access.log")

    handlers = [dj_info_handler,
                dj_error_handler,
                guni_error_handler,
                guni_access_handler]

    formatter = JsonFormatter("%(asctime)s"
                              " - %(process)s"
                              " - %(name)s"
                              " - %(filename)s"
                              " - %(trace_id)s"
                              " - %(user_id)s"
                              " - %(impersonating)s"
                              " - %(threadName)s"
                              " - %(levelname)s"
                              " - %(message)s",
                              rename_fields={
                                  "asctime": "timestamp",
                                  "trace_id": "x_traceId",
                                  "user_id": "x_userId",
                                  "impersonating": "x_impersonating",
                                  "levelname": "level",
                                  "threadName": "thread",
                                  "filename": "logger"
                              })
    for handler in handlers:
        handler.setFormatter(formatter)
    return handlers


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

    def __init__(self, host='0.0.0.0', port=DEFAULT_TCP_LOGGING_PORT, handler=LogRecordStreamHandler):
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
    logging.basicConfig(level=logging.INFO,
                        handlers=configure_handlers())
    tcp_server = LogRecordSocketReceiver()
    tcp_server.serve_until_stopped()


if __name__ == '__main__':
    main()
