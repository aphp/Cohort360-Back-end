# https://docs.python.org/3.11/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network
# https://docs.python.org/3.11/howto/logging-cookbook.html#running-a-logging-socket-listener-in-production
import logging
import pickle
import socketserver
import struct
from logging.handlers import RotatingFileHandler, DEFAULT_TCP_LOGGING_PORT
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class CustomRotatingFileHandler(RotatingFileHandler):

    def __init__(self, name, *args, **kwargs):
        super(CustomRotatingFileHandler, self).__init__(*args, **kwargs)
        self.name = name

    def handle(self, record):
        if record.name == self.name:
            return super(CustomRotatingFileHandler, self).handle(record)
        pass


def configure_logger() -> logging.Logger:
    logger = logging.getLogger("super_logger")
    logger.setLevel(logging.INFO)

    rotation_basis = dict(backupCount=1000, maxBytes=100 * 1024 * 1024)
    f = logging.Formatter('%(asctime)s %(processName)-10s %(process)-10s %(name)s %(levelname)-8s %(message)s')

    dj_info_handler = CustomRotatingFileHandler(name='info', filename=BASE_DIR / "log/django.log", **rotation_basis)
    dj_error_handler = CustomRotatingFileHandler(name='django.request', filename=BASE_DIR / "log/django.error.log", **rotation_basis)
    guni_error_handler = CustomRotatingFileHandler(name='gunicorn.error', filename=BASE_DIR / "log/gunicorn.error.log", **rotation_basis)
    guni_access_handler = CustomRotatingFileHandler(name='gunicorn.access', filename=BASE_DIR / "log/gunicorn.access.log", **rotation_basis)

    dj_info_handler.setFormatter(f)
    dj_error_handler.setFormatter(f)
    guni_access_handler.setFormatter(f)
    guni_error_handler.setFormatter(f)

    logger.addHandler(dj_info_handler)
    logger.addHandler(dj_error_handler)
    logger.addHandler(guni_error_handler)
    logger.addHandler(guni_access_handler)
    return logger


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
            obj = self.unPickle(chunk)
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)

    def unPickle(self, data):
        return pickle.loads(data)

    def handleLogRecord(self, record):
        logger = configure_logger()
        logger.handle(record)


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver suitable for testing.
    """
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
    # logging.basicConfig(format='%(relativeCreated)5d %(name)-15s **%(levelname)-8s** %(message)s')
    print('Starting TCP socket server...')
    tcp_server = LogRecordSocketReceiver()
    tcp_server.serve_until_stopped()


if __name__ == '__main__':
    main()
