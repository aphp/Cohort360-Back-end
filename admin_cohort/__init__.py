__title__ = 'Portail API'
__version__ = '3.5.2'
__author__ = 'Assistance Publique - Hopitaux de Paris, Département I&D'


from .celery import app

__all__ = ('app',)
