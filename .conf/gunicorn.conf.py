from setup_logging import SHARED_QUEUE
# from pathlib import Path
#
# BASE_DIR = Path(__file__).resolve().parent.parent

workers = 7
threads = 10

# capture_output = True

# accesslog = str(BASE_DIR / "log/gunicorn.access.log")
# errorlog = str(BASE_DIR / "log/gunicorn.error.log")

logconfig_dict = dict(
    version=1,
    disable_existing_loggers=False,
    root={"level": "INFO", "handlers": ["console"]},
    loggers={
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["error_queue"],
            "propagate": False,
            "qualname": "gunicorn.error"
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["access_queue"],
            "propagate": False,
            "qualname": "gunicorn.access"
        }},
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stdout"
        },
        "access_queue": {
            "class": "logging.handlers.QueueHandler",
            "queue": SHARED_QUEUE,
            "formatter": "generic"
        },
        "error_queue": {
            "class": "logging.handlers.QueueHandler",
            "queue": SHARED_QUEUE,
            "formatter": "generic"
        }},
    formatters={
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter"
        }
    }
)
