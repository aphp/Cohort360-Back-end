__title__ = 'Portail/Cohort360 API'
__version__ = '3.21.10'
__author__ = 'Assistance Publique - Hopitaux de Paris, Département I&D'


from .celery import celery_app

__all__ = ['celery_app']
