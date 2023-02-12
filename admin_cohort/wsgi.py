"""
WSGI config for admin_cohort project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""
import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_cohort.settings')

application = get_wsgi_application()

# def get_wsgi_app():
#     from setup_logging import setup_logging
#     app = get_wsgi_application()
#     print("***********      wsgi app")
#     setup_logging()
#     return app


# application = get_wsgi_app()
