# https://docs.python.org/3.11/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network
# https://docs.python.org/3.11/howto/logging-cookbook.html#running-a-logging-socket-listener-in-production
import json
import logging
import socketserver
import struct
from logging.handlers import DEFAULT_TCP_LOGGING_PORT
from pathlib import Path
from typing import List

from pythonjsonlogger.json import JsonFormatter

INFO_HANDLER = 'info'
ERROR_HANDLER = 'error'
CELERY_HANDLER = 'celery'
GUNICORN_HANDLER = 'gunicorn.error'

BASE_DIR = Path(__file__).resolve().parent


class CustomFileHandler(logging.FileHandler):

    def __init__(self, name, *args, **kwargs):
        # each handler has filename matching its name
        kwargs["filename"] = BASE_DIR / f"log/{name}.log"
        super().__init__(*args, **kwargs)
        self.name = name

    @staticmethod
    def get_handler_name(record: logging.LogRecord) -> str:
        record_name = record.name
        if 'celery' in record_name:                                               # Route Celery related logs
            return CELERY_HANDLER
        if record_name == GUNICORN_HANDLER:                                       # Route Gunicorn errors
            return GUNICORN_HANDLER
        if record_name.startswith('django') or record.levelno >= logging.ERROR:   # Route Django/DRF errors
            return ERROR_HANDLER
        return INFO_HANDLER                                                       # Route logs from apps (and maybe other logs)

    def handle(self, record: logging.LogRecord):
        """
        This is the core routing logic. It renames incoming log records
        to match the target log file handler.
         - cover all loggers created in modules ex: admin_cohort.views.users.py
         - cover all Celery loggers like: celery, celery.task, celery.worker, ...
        """
        handler_name = self.get_handler_name(record)
        if handler_name == self.name:
            return super().handle(record)
        return None


def configure_handlers() -> List[logging.Handler]:
    handlers = [CustomFileHandler(name=name) for name in (INFO_HANDLER, ERROR_HANDLER, CELERY_HANDLER, GUNICORN_HANDLER)]
    formatter = JsonFormatter("%(name)s"
                              " - %(filename)s"
                              " - %(message)s"
                              " - %(asctime)s"
                              " - %(process)s"
                              " - %(trace_id)s"
                              " - %(user_id)s"
                              " - %(impersonating)s"
                              " - %(levelname)s",
                              rename_fields={
                                  "asctime": "timestamp",
                                  "trace_id": "x_traceId",
                                  "user_id": "x_userId",
                                  "impersonating": "x_impersonating",
                                  "levelname": "level",
                                  "filename": "logger"
                              })
    for handler in handlers:
        handler.setFormatter(formatter)
    return handlers


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    def handle(self):
        """ Handle multiple requests - each expected to be a 4-byte length,
            followed by the LogRecord in pickle format. Logs the record
            according to whatever policy is configured locally.
        """
        logger = logging.getLogger('root')

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
            logger.handle(record)


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, host='0.0.0.0', port=DEFAULT_TCP_LOGGING_PORT, handler=LogRecordStreamHandler):
        super().__init__(server_address=(host, port), RequestHandlerClass=handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, _, _ = select.select([self.socket.fileno()], [], [], self.timeout)
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
