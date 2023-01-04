# https://docs.gunicorn.org/en/stable/settings.html#workers

workers = 7
threads = 10

capture_output = True

logconfig_dict = dict(
    version=1,
    disable_existing_loggers=False,
    root={"level": "INFO", "handlers": ["console"]},
    loggers={
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["error_file"],
            "propagate": True,
            "qualname": "gunicorn.error"
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["access_file"],
            "propagate": True,
            "qualname": "gunicorn.access"
        }
    },
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stdout"
        },
        "access_file": {
            "class": "logging.FileHandler",
            "filename": "/app/log/gunicorn.access.log",
            "formatter": "generic",
        },
        "error_file": {
            "class": "logging.FileHandler",
            "filename": "/app/log/gunicorn.error.log",
            "formatter": "generic",
        },
    },
    formatters={
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter"
        }
    }
)
