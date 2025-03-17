import logging
import tomllib
from logging.handlers import DEFAULT_TCP_LOGGING_PORT
from pathlib import Path

import environ
import pytz
from celery.schedules import crontab


def get_project_info():
    pyproject_file = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_file, "rb") as f:
        pyproject = tomllib.load(f)
    project_info = pyproject.get("project", {})
    return (project_info.get("name"),
            project_info.get('version'),
            project_info.get("description"))


TITLE, VERSION, DESCRIPTION = get_project_info()

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env()

NOTSET = environ.Env.NOTSET

BACK_HOST = env.str("BACK_HOST", default="localhost:8000")
BACK_URL = f"https://{BACK_HOST}"
FRONT_URL = env.str("FRONT_URL", default="http://localhost:3000")
FRONT_URLS = env.str("FRONT_URLS", default="http://localhost:3000").split(',')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
# Debug will also send sensitive data with the response to an error
DEBUG = env.bool("DEBUG", default=False)

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

ADMINS = [a.split(',') for a in env("ADMINS", default="").split(';')]

NOTIFY_ADMINS = env.bool("NOTIFY_ADMINS", default=False)

# logging
logging.captureWarnings(True)

SOCKET_LOGGER_HOST = env("SOCKET_LOGGER_HOST", default="localhost")
LOGGING = dict(version=1,
               disable_existing_loggers=False,
               loggers={
                   'info': {
                       'level': "INFO",
                       'handlers': ['info', 'console'],
                       'propagate': False
                   },
                   'django.request': {
                       'level': "ERROR",
                       'handlers': ['error', 'console'] + (NOTIFY_ADMINS and ['mail_admins'] or []),
                       'propagate': False
                   }
               },
               filters={
                   "request_headers_interceptor": {
                       "()": "admin_cohort.tools.logging.RequestHeadersInterceptorFilter"
                   },
               },
               handlers={
                   'console': {
                       'level': "INFO",
                       'class': "logging.StreamHandler",
                       'filters': ["request_headers_interceptor"]
                   },
                   'info': {
                       'level': "INFO",
                       'class': "admin_cohort.tools.logging.CustomSocketHandler",
                       'host': SOCKET_LOGGER_HOST,
                       'port': DEFAULT_TCP_LOGGING_PORT,
                       'filters': ["request_headers_interceptor"]
                   },
                   'error': {
                       'level': "ERROR",
                       'class': "admin_cohort.tools.logging.CustomSocketHandler",
                       'host': SOCKET_LOGGER_HOST,
                       'port': DEFAULT_TCP_LOGGING_PORT,
                       'filters': ["request_headers_interceptor"]
                   },
                   'mail_admins': {
                       'level': "ERROR",
                       'class': "django.utils.log.AdminEmailHandler",
                       'include_html': True
                   }
               })

# Application definition
INCLUDED_APPS = env('INCLUDED_APPS',
                    default='accesses,content_management,cohort_job_server,'
                            'cohort,exports,accesses_fhir_perimeters').split(",")

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
                  'admin_cohort'
                  ] + INCLUDED_APPS

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
    'admin_cohort.middleware.context_request_middleware.ContextRequestMiddleware',
    'admin_cohort.middleware.jwt_session_middleware.JWTSessionMiddleware',
    'admin_cohort.middleware.swagger_headers_middleware.SwaggerHeadersMiddleware'
]

INFLUXDB_ENABLED = env.bool("INFLUXDB_ENABLED", default=False)

if INFLUXDB_ENABLED:
    MIDDLEWARE = ['admin_cohort.middleware.influxdb_middleware.InfluxDBMiddleware'] + MIDDLEWARE

TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates',
              'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True,
              'OPTIONS': {'context_processors': ['django.template.context_processors.debug',
                                                 'django.template.context_processors.request',
                                                 'django.contrib.auth.context_processors.auth',
                                                 'django.contrib.messages.context_processors.messages']
                          }
              }]

DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
                         'NAME': env("DB_AUTH_NAME"),
                         'USER': env("DB_AUTH_USER"),
                         'PASSWORD': env("DB_AUTH_PASSWORD"),
                         'HOST': env("DB_AUTH_HOST"),
                         'PORT': env("DB_AUTH_PORT"),
                         'TEST': {'NAME': f'test_{env("DB_AUTH_NAME")}'}
                         }
             }

WSGI_APPLICATION = 'admin_cohort.wsgi.application'

ROOT_URLCONF = 'admin_cohort.urls'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

AUTH_USER_MODEL = 'admin_cohort.User'

APPEND_SLASH = False

LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_TZ = True
TIME_ZONE = 'UTC'
USE_DEPRECATED_PYTZ = True
utc = pytz.UTC

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'


AUTHENTICATION_BACKENDS = ['admin_cohort.auth.auth_backends.JWTAuthBackend',
                           'admin_cohort.auth.auth_backends.OIDCAuthBackend']

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': ['admin_cohort.auth.auth_class.Authentication'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend',
                                'rest_framework.filters.SearchFilter'],
    'PAGE_SIZE': 20
}

PAGINATION_MAX_LIMIT = 30_000

SPECTACULAR_SETTINGS = {"TITLE": TITLE,
                        "DESCRIPTION": DESCRIPTION,
                        "VERSION": VERSION,
                        "SERVE_AUTHENTICATION": [],
                        "SERVE_INCLUDE_SCHEMA": False,
                        "COMPONENT_SPLIT_REQUEST": True,
                        "SORT_OPERATION_PARAMETERS": False,
                        "SWAGGER_UI_SETTINGS": {
                            "filter": True,
                            "docExpansion": "none",
                            "tagsSorter": "alpha",
                            "operationsSorter": "method",
                            "tryItOutEnabled": True,
                            "withCredentials": True,
                            "persistAuthorization": True,
                        },
                        }

# EMAILS
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST = env.str("EMAIL_HOST", default="")
EMAIL_PORT = env.str("EMAIL_PORT", default="")
EMAIL_SUPPORT_CONTACT = env.str("EMAIL_SUPPORT_CONTACT", default="")
EMAIL_SENDER_ADDRESS = env.str("EMAIL_SENDER_ADDRESS", default="")
EMAIL_REGEX_CHECK = env.str("EMAIL_REGEX_CHECK", default=r"^[\w.+-]+@[\w-]+\.[\w]+$")

# Celery
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://localhost:6379")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

DEFAULT_LOCAL_TASKS = """
count_users_on_perimeters,accesses.tasks.count_users_on_perimeters,5,30;
check_expiring_accesses,accesses.tasks.check_expiring_accesses,6,0
"""
MAINTENANCE_PERIODIC_SCHEDULING_MINUTES = env("MAINTENANCE_PERIODIC_SCHEDULING", default=1)
LOCAL_TASKS = env('LOCAL_TASKS', default=DEFAULT_LOCAL_TASKS)
if LOCAL_TASKS:
    CELERY_BEAT_SCHEDULE = {'maintenance_notifier': {
        'task': 'admin_cohort.tasks.maintenance_notifier_checker',
        'schedule': crontab(minute=f'*/{MAINTENANCE_PERIODIC_SCHEDULING_MINUTES}')
    },
        **{task_name: {'task': task,
                       'schedule': crontab(hour=hour,
                                           minute=minute)}
           for (task_name, task, hour, minute) in
           [task.strip().split(',')
            for task in LOCAL_TASKS.split(';')]
           }}

# CONSTANTS
utc = pytz.UTC

ACCESS_SOURCES = ["Manual", "ORBIS"]
PERIMETER_TYPES = env("PERIMETER_TYPES").split(",")
ROOT_PERIMETER_TYPE = PERIMETER_TYPES[0]
ROOT_PERIMETER_ID = env.int("ROOT_PERIMETER_ID", default=0)
SHARED_FOLDER_NAME = 'Mes requêtes reçues'

SESSION_COOKIE_NAME = "sessionid"
SESSION_COOKIE_AGE = 24 * 60 * 60

ENABLE_JWT = env.bool("ENABLE_JWT", default=True)

if ENABLE_JWT:
    SIMPLE_JWT = {"USER_ID_FIELD": "username",
                  "USER_ID_CLAIM": "username",
                  "SIGNING_KEY": env.str("JWT_SIGNING_KEY"),
                  "ROTATE_REFRESH_TOKENS": True,
                  }

    ID_CHECKER_URL = env.str("ID_CHECKER_URL")
    ID_CHECKER_HEADER = env.str("ID_CHECKER_TOKEN_HEADER")
    ID_CHECKER_TOKEN = env.str("ID_CHECKER_TOKEN")
    ID_CHECKER_HEADERS = {ID_CHECKER_HEADER: ID_CHECKER_TOKEN}

JWT_AUTH_MODE = "JWT"
OIDC_AUTH_MODE = "OIDC"

AUTHORIZATION_METHOD_HEADER = "AUTHORIZATIONMETHOD"
TRACE_ID_HEADER = "X-Trace-Id"
IMPERSONATING_HEADER = "X-Impersonate"

# CUSTOM EXCEPTION REPORTER
DEFAULT_EXCEPTION_REPORTER_FILTER = 'admin_cohort.tools.except_report_filter.CustomExceptionReporterFilter'

# COHORTS +20k
LAST_COUNT_VALIDITY = env.int("LAST_COUNT_VALIDITY", default=24)  # in hours
COHORT_LIMIT = env.int("COHORT_LIMIT", default=20_000)

# InfluxDB
INFLUXDB_TOKEN = env("INFLUXDB_DJANGO_TOKEN", default=NOTSET if INFLUXDB_ENABLED else "")
INFLUXDB_URL = env("INFLUXDB_URL", default=NOTSET if INFLUXDB_ENABLED else "")
INFLUXDB_ORG = env("INFLUXDB_ORG", default=NOTSET if INFLUXDB_ENABLED else "")
INFLUXDB_BUCKET = env("INFLUXDB_BUCKET", default=NOTSET if INFLUXDB_ENABLED else "")

# CACHE
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CELERY_BROKER_URL
    }
}
if not env.bool("ENABLE_CACHE", default=False):
    CACHES = {'default': {'BACKEND': 'admin_cohort.tools.cache.CustomDummyCache'}}

REST_FRAMEWORK_EXTENSIONS = {"DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX": "",
                             "DEFAULT_USE_CACHE": "default",
                             "DEFAULT_CACHE_RESPONSE_TIMEOUT": 24 * 60 * 60,
                             "DEFAULT_CACHE_KEY_FUNC": "admin_cohort.tools.cache.construct_cache_key",
                             "DEFAULT_CACHE_ERRORS": False
                             }

# ACCESSES
ACCESS_MANAGERS_LIST_LINK = env.str("ACCESS_MANAGERS_LIST_LINK", default="")
ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS = env.int("ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS", default=30)
ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS = env.int("ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS", default=2)
MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS = env.int("ACCESS_MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS", default=2 * 365)

# COHORT_JOB_SERVER
CRB_TEST_FHIR_QUERIES = env.bool("CRB_TEST_FHIR_QUERIES", default=False)
USE_SOLR = env.bool("USE_SOLR", default=False)

# EXPORTS
DAYS_TO_KEEP_EXPORTED_FILES = env.int("DAYS_TO_KEEP_EXPORTED_FILES", default=7)

# WebSockets
WEBSOCKET_MANAGER = {"module": "admin_cohort.services.ws_event_manager",
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
