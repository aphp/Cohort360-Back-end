import gunicorn.app.base

from admin_cohort.settings import SHARED_QUEUE
from admin_cohort.wsgi import application
from setup_logging import setup_logging




class DjangoWSGI(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


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

if __name__ == '__main__':
    options = {'workers': 7,
               'threads': 10,
               'logconfig_dict': logconfig_dict
               }
    setup_logging(queue=SHARED_QUEUE)
    DjangoWSGI(application, options).run()
