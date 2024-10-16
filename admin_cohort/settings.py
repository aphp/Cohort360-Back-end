import logging
from datetime import date, datetime, time
from logging.handlers import DEFAULT_TCP_LOGGING_PORT
from pathlib import Path

import environ
import pytz
from celery.schedules import crontab

TITLE = "Portail/Cohort360 API"
VERSION = "3.23.16"
AUTHOR = "Assistance Publique - Hopitaux de Paris, Département I&D"
DESCRIPTION_MD = f"""Supports the official **Cohort360** web app and **Portail**  
                     Built by **{AUTHOR}**
                  """

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env()

BACK_HOST = env("BACK_HOST")
BACK_URL = f"https://{env('BACK_HOST')}"
FRONT_URL = env("FRONT_URL")
FRONT_URLS = env("FRONT_URLS").split(',')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
# Debug will also send sensitive data with the response to an error
DEBUG = int(env("DEBUG")) == 1

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [BACK_URL] + FRONT_URLS
CSRF_TRUSTED_ORIGINS = [BACK_URL] + FRONT_URLS

CORS_ALLOW_HEADERS = ['access-control-allow-origin',
                      'content-type',
                      'Authorization',
                      'X-CSRFToken']

ALLOWED_HOSTS = ['localhost',
                 '127.0.0.1',
                 '0.0.0.0',
                 BACK_HOST]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
ACCESS_TOKEN_COOKIE_SECURE = not DEBUG

ADMINS = [a.split(',') for a in env("ADMINS").split(';')]
NOTIFY_ADMINS = bool(env("NOTIFY_ADMINS", default=False))

logging.captureWarnings(True)

LOGGING = dict(version=1,
               disable_existing_loggers=False,
               loggers={
                   'info': {
                       'level': "INFO",
                       'handlers': ['info_handler'] + (DEBUG and ['console'] or []),
                       'propagate': False
                   },
                   'django.request': {
                       'level': "ERROR",
                       'handlers': ['error_handler'] + (DEBUG and ['console'] or []) + (
                               NOTIFY_ADMINS and ['mail_admins'] or []),
                       'propagate': False
                   }
               },
               handlers={
                   'console': {
                       'level': "INFO",
                       'class': "logging.StreamHandler"
                   },
                   'info_handler': {
                       'level': "INFO",
                       'class': "admin_cohort.tools.logging.CustomSocketHandler",
                       'host': "localhost",
                       'port': DEFAULT_TCP_LOGGING_PORT,
                   },
                   'error_handler': {
                       'level': "ERROR",
                       'class': "admin_cohort.tools.logging.CustomSocketHandler",
                       'host': "localhost",
                       'port': DEFAULT_TCP_LOGGING_PORT,
                   },
                   'mail_admins': {
                       'level': "ERROR",
                       'class': "django.utils.log.AdminEmailHandler",
                       'include_html': True
                   }
               })

# Application definition
INCLUDED_APPS = env('INCLUDED_APPS', default='accesses,cohort_job_server,cohort,exports').split(",")
INFLUXDB_DISABLED = int(env("INFLUXDB_DISABLED")) == 1
ENABLE_JWT = env("ENABLE_JWT", default=False)

INSTALLED_APPS = ['django.contrib.admin',
                  'django.contrib.auth',
                  'django.contrib.contenttypes',
                  'django.contrib.sessions',
                  'django.contrib.messages',
                  'django.contrib.staticfiles',
                  'django_extensions',
                  'corsheaders',
                  'django_filters',
                  'rest_framework',
                  'drf_spectacular',
                  'rest_framework_tracking',
                  'safedelete',
                  'channels',
                  'django_celery_beat',
                  'admin_cohort'] + INCLUDED_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'admin_cohort.middleware.maintenance_middleware.MaintenanceModeMiddleware',
    'admin_cohort.middleware.request_trace_id_middleware.RequestTraceIdMiddleware',
    'admin_cohort.middleware.jwt_session_middleware.JWTSessionMiddleware',
    'admin_cohort.middleware.swagger_headers_middleware.SwaggerHeadersMiddleware'
    ]
MIDDLEWARE = ((['admin_cohort.middleware.influxdb_middleware.InfluxDBMiddleware'] if not INFLUXDB_DISABLED else []) +
              MIDDLEWARE)

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False

AUTHENTICATION_BACKENDS = ['admin_cohort.auth.auth_backends.JWTAuthBackend',
                           'admin_cohort.auth.auth_backends.OIDCAuthBackend']

ROOT_URLCONF = 'admin_cohort.urls'

TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates',
              'DIRS': [BASE_DIR / 'admin_cohort/templates'] +
                      [BASE_DIR / f'{app}/templates' for app in INCLUDED_APPS],
              'APP_DIRS': True,
              'OPTIONS': {'context_processors': ['django.template.context_processors.debug',
                                                 'django.template.context_processors.request',
                                                 'django.contrib.auth.context_processors.auth',
                                                 'django.contrib.messages.context_processors.messages']
                          }
              }]

WSGI_APPLICATION = 'admin_cohort.wsgi.application'

DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
                         'NAME': env("DB_AUTH_NAME"),
                         'USER': env("DB_AUTH_USER"),
                         'PASSWORD': env("DB_AUTH_PASSWORD"),
                         'HOST': env("DB_AUTH_HOST"),
                         'PORT': env("DB_AUTH_PORT"),
                         'TEST': {'NAME': 'test_portail'}
                         }
             }

LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_TZ = True
TIME_ZONE = 'UTC'
USE_DEPRECATED_PYTZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

REST_FRAMEWORK = {'DEFAULT_PERMISSION_CLASSES': ['admin_cohort.permissions.IsAuthenticated'],
                  'DEFAULT_AUTHENTICATION_CLASSES': ['admin_cohort.auth.auth_class.Authentication'],
                  'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
                  'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
                  'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend',
                                              'rest_framework.filters.SearchFilter'],
                  'PAGE_SIZE': 20
                  }

PAGINATION_MAX_LIMIT = 30_000

SPECTACULAR_SETTINGS = {"TITLE": TITLE,
                        "DESCRIPTION": DESCRIPTION_MD,
                        "VERSION": VERSION,
                        "SERVE_INCLUDE_SCHEMA": False,
                        "COMPONENT_SPLIT_REQUEST": True,
                        "SORT_OPERATION_PARAMETERS": False,
                        "SWAGGER_UI_SETTINGS": {
                            "withCredentials": True,
                            "persistAuthorization": True,
                            "oauth2RedirectUrl": f"{env('OIDC_SWAGGER_REDIRECT_URL')}",
                            },
                        "SWAGGER_UI_OAUTH2_CONFIG": {
                            "appName": TITLE,
                            "issuer": env('OIDC_AUTH_SERVER_1', default=''),
                            "realm": env('OIDC_AUTH_SERVER_1', default='').split("realms/")[-1],
                            "clientId": env('OIDC_CLIENT_ID_1', default=''),
                            "useBasicAuthenticationWithAccessCodeGrant": True,
                            },
                        }

APPEND_SLASH = False

AUTH_USER_MODEL = 'admin_cohort.User'

# EMAILS
EMAIL_USE_TLS = env("EMAIL_USE_TLS").lower() == "true"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_SUPPORT_CONTACT = env("EMAIL_SUPPORT_CONTACT")
EMAIL_SENDER_ADDRESS = env("EMAIL_SENDER_ADDRESS")
EMAIL_REGEX_CHECK = env("EMAIL_REGEX_CHECK", default=r"^[\w.+-]+@[\w-]+\.[\w]+$")

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

DEFAULT_LOCAL_TASKS = """
count_users_on_perimeters,accesses.tasks.count_users_on_perimeters,5,30;
check_expiring_accesses,accesses.tasks.check_expiring_accesses,6,0
"""
LOCAL_TASKS = env('LOCAL_TASKS', default=DEFAULT_LOCAL_TASKS)
if LOCAL_TASKS:
    CELERY_BEAT_SCHEDULE = {task_name: {'task': task,
                                        'schedule': crontab(hour=hour, minute=minute)}
                            for (task_name, task, hour, minute) in [task.strip().split(',')
                                                                    for task in LOCAL_TASKS.split(';')]
                            }

# CONSTANTS
utc = pytz.UTC

MANUAL_SOURCE = "Manual"
PERIMETERS_TYPES = env("PERIMETER_TYPES").split(",")
ROOT_PERIMETER_TYPE = PERIMETERS_TYPES[0]
SHARED_FOLDER_NAME = 'Mes requêtes reçues'
MODEL_MANUAL_START_DATE_DEFAULT_ON_UPDATE = utc.localize(datetime.combine(date(1970, 1, 1), time.min))
MODEL_MANUAL_END_DATE_DEFAULT_ON_UPDATE = utc.localize(datetime.combine(date(2070, 1, 1), time.min))

ACCESS_TOKEN_COOKIE = "access_token"
SESSION_COOKIE_NAME = "sessionid"
SESSION_COOKIE_AGE = 24 * 60 * 60

JWT_AUTH_MODE = "JWT"
OIDC_AUTH_MODE = "OIDC"

# CUSTOM EXCEPTION REPORTER
DEFAULT_EXCEPTION_REPORTER_FILTER = 'admin_cohort.tools.except_report_filter.CustomExceptionReporterFilter'
SENSITIVE_PARAMS = env('SENSITIVE_PARAMS').split(",")

# COHORTS +20k
LAST_COUNT_VALIDITY = int(env("LAST_COUNT_VALIDITY", default=24))  # in hours
COHORT_LIMIT = int(env("COHORT_LIMIT", default=20_000))

ROLLOUT_USERNAME = env("ROLLOUT_USERNAME", default="ROLLOUT_PIPELINE")

# InfluxDB
INFLUXDB_TOKEN = env("INFLUXDB_DJANGO_TOKEN", default="" if INFLUXDB_DISABLED else environ.Env.NOTSET)
INFLUXDB_URL = env("INFLUXDB_URL", default="" if INFLUXDB_DISABLED else environ.Env.NOTSET)
INFLUXDB_ORG = env("INFLUXDB_ORG", default="" if INFLUXDB_DISABLED else environ.Env.NOTSET)
INFLUXDB_BUCKET = env("INFLUXDB_BUCKET", default="" if INFLUXDB_DISABLED else environ.Env.NOTSET)

# CACHE
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CELERY_BROKER_URL
    }
}
if not env.bool("ENABLE_CACHE"):
    CACHES = {'default': {'BACKEND': 'admin_cohort.tools.cache.CustomDummyCache'}}

REST_FRAMEWORK_EXTENSIONS = {"DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX": "",
                             "DEFAULT_USE_CACHE": "default",
                             "DEFAULT_CACHE_RESPONSE_TIMEOUT": 24 * 60 * 60,
                             "DEFAULT_CACHE_KEY_FUNC": "admin_cohort.tools.cache.construct_cache_key",
                             "DEFAULT_CACHE_ERRORS": False
                             }

# ACCESSES
ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS = int(env("ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS", default=30))
ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS = int(env("ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS", default=2))
MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS = int(env("ACCESS_MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS", default=2 * 365))

# COHORT_JOB_SERVER
CRB_TEST_FHIR_QUERIES = bool(env("CRB_TEST_FHIR_QUERIES", default=False))
USE_SOLR = bool(env("USE_SOLR", default=False))

# EXPORTS
DAYS_TO_KEEP_EXPORTED_FILES = int(env("DAYS_TO_KEEP_EXPORTED_FILES", default=7))

# WebSockets
WEBSOCKET_MANAGER = {"module": "cohort.services.ws_event_manager",
                     "manager_class": "WebsocketManager"
                     }

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [CELERY_BROKER_URL],
        },
    },
}
