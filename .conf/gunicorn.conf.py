import os
from logging.handlers import DEFAULT_TCP_LOGGING_PORT

from environ import environ
from gunicorn.glogging import Logger
from prometheus_client import multiprocess

env = environ.Env()
workers = 7
threads = 10
limit_request_line = 8190
timeout = 1800


class CustomLogger(Logger):
    def atoms(self, resp, req, environ, request_time):
        atoms = super().atoms(resp, req, environ, request_time)
        atoms.update(
            {
                "user_id": environ.get("user_id", "---"),
                "trace_id": environ.get("trace_id", "---"),
                "impersonating": environ.get("impersonating", "---"),
            }
        )
        return atoms


SOCKET_LOGGER_HOST = env("SOCKET_LOGGER_HOST", default="localhost")

logger_class = CustomLogger

logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"level": "INFO", "handlers": ["socket_handler", "console"]},
    "loggers": {
        "gunicorn.error": {"level": "INFO", "handlers": ["socket_handler", "console"], "propagate": False, "qualname": "gunicorn.error"},
        "gunicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False, "qualname": "gunicorn.access"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "generic", "stream": "ext://sys.stdout"},
        "socket_handler": {
            "class": "admin_cohort.tools.logging.CustomSocketHandler",
            "host": SOCKET_LOGGER_HOST,
            "port": DEFAULT_TCP_LOGGING_PORT,
        },
    },
}


def child_exit(server, worker):
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.mark_process_dead(worker.pid)
