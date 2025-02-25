
from django.apps import AppConfig


class ContentManagementConfig(AppConfig):
    name = 'content_management'

    CONTENT_TYPES = {
        'BANNER_WARNING': {
            'label': "Bannière d'avertissement",
            'description': "Bannière d'avertissement"
        },
        'BANNER_INFO': {
            'label': 'Bannière d\'information',
            'description': 'Bannière d\'information'
        },
        'BANNER_ERROR': {
            'label': 'Bannière d\'erreur',
            'description': 'Bannière d\'erreur'
        },
        'RELEASE_NOTE': {
            'label': 'Note de version',
            'description': 'Note de version'
        }
    }
