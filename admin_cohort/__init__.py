__title__ = 'Portail API'
__version__ = '3.7.6'
__author__ = 'Assistance Publique - Hopitaux de Paris, Département I&D'


from .celery import app

__all__ = ('app',)
