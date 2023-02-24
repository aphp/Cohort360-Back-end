from logging.handlers import DEFAULT_TCP_LOGGING_PORT

workers = 7
threads = 10

logconfig_dict = dict(
    version=1,
    disable_existing_loggers=False,
    root={"level": "INFO", "handlers": ["error"]},
    loggers={
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["error"],
            "propagate": False,
            "qualname": "gunicorn.error"
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["access"],
            "propagate": False,
            "qualname": "gunicorn.access"
        }},
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stdout"
        },
        "access": {
            "class": "admin_cohort.tools.CustomSocketHandler",
            "host": "localhost",
            "port": DEFAULT_TCP_LOGGING_PORT,
            "formatter": "generic"
        },
        "error": {
            "class": "admin_cohort.tools.CustomSocketHandler",
            "host": "localhost",
            "port": DEFAULT_TCP_LOGGING_PORT,
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
