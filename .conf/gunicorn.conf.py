from logging.handlers import DEFAULT_TCP_LOGGING_PORT

workers = 7
threads = 10
limit_request_line = 8190

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
            "class": "admin_cohort.tools.logging.CustomSocketHandler",
            "host": "localhost",
            "port": DEFAULT_TCP_LOGGING_PORT,
        },
        "error": {
            "class": "admin_cohort.tools.logging.CustomSocketHandler",
            "host": "localhost",
            "port": DEFAULT_TCP_LOGGING_PORT,
        }}
)
