from .celery import celery_app

# unused import, only done for the interpreter to load the scheme
from admin_cohort.tools.swagger import SwaggerOIDCAuthScheme

__all__ = ['celery_app',
           'SwaggerOIDCAuthScheme']
