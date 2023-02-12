import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import Queue, Process
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

SHARED_QUEUE = Queue()


class CustomLogsFilter(logging.Filter):

    def filter(self, record):
        res = super(CustomLogsFilter, self).filter(record)
        logger = logging.getLogger('super_logger')
        # todo: attach a handler according to the source of the log record...
        return res


def configure_logger() -> logging.Logger:
    """ todo: configure Django/Gunicorn loggers here. logging.config.dictConfig(config).
        todo: override def handle() on Logger class to dispatch log records on handlers.
    """
    rotation_basis = dict(backupCount=1000,
                          maxBytes=100 * 1024 * 1024)

    logger = logging.getLogger("super_logger")
    logger.setLevel(logging.INFO)

    # logger.addFilter(CustomLogsFilter())

    dj_error_handler = RotatingFileHandler(filename=BASE_DIR / "log/django.error.log", **rotation_basis)
    dj_info_handler = RotatingFileHandler(filename=BASE_DIR / "log/django.info.log", **rotation_basis)
    guni_error_handler = RotatingFileHandler(filename=BASE_DIR / "log/gunicorn.error.log", **rotation_basis)
    guni_access_handler = RotatingFileHandler(filename=BASE_DIR / "log/gunicorn.access.log", **rotation_basis)

    f = logging.Formatter('%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')
    dj_info_handler.setFormatter(f)
    dj_error_handler.setFormatter(f)
    guni_access_handler.setFormatter(f)
    guni_error_handler.setFormatter(f)

    logger.addHandler(dj_error_handler)
    logger.addHandler(dj_info_handler)
    logger.addHandler(guni_error_handler)
    logger.addHandler(guni_access_handler)
    return logger


def log_listener_process(queue: Queue):
    logger = configure_logger()
    while True:
        try:
            record = queue.get()
            print(f"************ {record=}", flush=True)
            if record is None:
                break
            logger.handle(record)  # No level or filter logic applied - just do it!
        except Exception:
            import sys, traceback
            print('Whoops! Problem:', file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)


def setup_logging(queue):
    logger_p = Process(target=log_listener_process, args=(queue,))
    logger_p.start()
    print(f"************ {logger_p.pid=}")


# if __name__ == "__main__":
#     """ run gunicorn command here ?"""
#     setup_logging()
