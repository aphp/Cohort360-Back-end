from rest_framework.views import exception_handler
import logging


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    view = context.get('view', None)
    request = context.get('request', None)
    logger.error(f"Exception in {view.__class__.__name__ if view else 'UnknownView'} | "
                 f"User: {request.user if request else 'Anonymous'} | "
                 f"{request.method if request else 'UnknownMethod'} {request.path if request else 'UnknownPath'} | "
                 f"{str(exc)}",
                 exc_info=True)
    return response
