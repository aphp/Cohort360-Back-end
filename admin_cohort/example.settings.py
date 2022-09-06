import os
import pytz
from datetime import date, datetime, time

# from django.utils.datetime_safe import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVER_VERSION = "dev"  # or prod
BACK_URL = ""
FRONT_URLS = []

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "test"

# SECURITY WARNING: don't run with debug turned on in production!
# Debug will also send sensitive data with the response to an error
DEBUG = True

CORS_ORIGIN_ALLOW_ALL = DEBUG
CORS_ALLOW_ALL_ORIGINS = DEBUG
if SERVER_VERSION == "dev":
    CORS_ORIGIN_WHITELIST = [
        "http://localhost:3000",
        "http://127.0.0.1"
    ]
    CSRF_TRUSTED_ORIGINS = [
        "localhost:3000",
        "127.0.0.1"
    ]

elif SERVER_VERSION == "prod":
    CORS_ORIGIN_WHITELIST = [
        "http://localhost:3000",
        BACK_URL,
        "http://localhost:49033",
    ] + FRONT_URLS
    CSRF_TRUSTED_ORIGINS = [
        BACK_URL,
        "http://localhost:49033",
        "127.0.0.1"
    ] + FRONT_URLS

CORS_ALLOW_HEADERS = [
    'access-control-allow-origin',
    'content-type',
    'Authorization',
    'X-CSRFToken'
    ]

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0',
                 BACK_URL]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ADMINS = [("Squall"), "squall@bgu.com"]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "{levelname} {asctime} module={module} "
                      "pid={process:d} tid={thread:d} msg=`{message}`",
            'style': "{",
        }
    },
    'handlers': {
        'console': {
            'level': "INFO",
            'class': "logging.StreamHandler",
            'formatter': "verbose"
        },
        'mail_admins': {
            'level': "ERROR",
            'class': "django.utils.log.AdminEmailHandler",
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': "ERROR",
            'propagate': False,
        }
    }
}

# Application definition
INCLUDED_APPS = ["accesses", "cohort", "workspaces", "exports"]
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',

    'corsheaders',
    'django_filters',
    'drf_yasg',
    'rest_framework',
    'rest_framework_swagger',
    'rest_framework_tracking',
    'safedelete',

    'admin_cohort',
] + INCLUDED_APPS

for app, example, conf in [
    ('admin_cohort', 'example_conf_auth', 'conf_auth'),
    ('accesses', 'example.conf_perimeters', 'conf_perimeters'),
    ('cohort', 'example.conf_cohort_job_api', 'conf_cohort_job_api'),
    ('exports', 'example_conf_exports', 'conf_exports'),
    ('workspaces', 'example.conf_workspaces', 'conf_workspaces'),
]:
    p = os.path.join(app, f"{conf}.py")
    if app in INSTALLED_APPS and not os.path.exists(p):
        raise Exception(
            f"You want '{app}' app, but {p} file could not be found."
            f"Check {app}.{conf} to build it.")


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "admin_cohort.MaintenanceModeMiddleware.MaintenanceModeMiddleware",
    'admin_cohort.AuthMiddleware.CustomJwtSessionMiddleware',
    "django_cprofile_middleware.middleware.ProfilerMiddleware",
]

DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False

AUTHENTICATION_BACKENDS = [
    'admin_cohort.backends.AuthBackend',
]

ROOT_URLCONF = 'admin_cohort.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'admin_cohort.wsgi.application'

DB_SCHEMAS = ["public", "accesses"]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': "portail_dev",
        'USER': "portail_dev_limited_rw",
        'PASSWORD': "portail_psswd",
        'HOST': "localhost",
        'PORT': "",
        'OPTIONS': {
            'options': f"-c search_path="
                       f"{','.join(DB_SCHEMAS)},"
                       f"public"
        },
        'TEST': {
            'NAME': 'test_portail',
        }
    },
}

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'admin_cohort.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'admin_cohort.AuthMiddleware.CustomAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        # 'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter'],
    'PAGE_SIZE': 100,
}

SWAGGER_SETTINGS = {
    "LOGOUT_URL": "/accounts/logout/",
    "LOGIN_URL": "/accounts/login/",
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_AUTO_SCHEMA_CLASS': "admin_cohort.views.CustomAutoSchema",
}

REST_FRAMEWORK_EXTENSIONS = {
    'DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX': '',
}

APPEND_SLASH = False

AUTH_USER_MODEL = 'admin_cohort.User'
LOGOUT_REDIRECT_URL = '/'

# EMAILS

EMAIL_USE_TLS = False
EMAIL_HOST = ""
EMAIL_PORT = ""
EMAIL_BACK_HOST_URL = ""
EMAIL_SUPPORT_CONTACT = ""
EMAIL_SENDER_ADDRESS = ""
EMAIL_REGEX_CHECK = ""

EXPORT_CSV_PATH = ""
EXPORT_DAYS_BEFORE_DELETE = 7

# Celery
CELERY_BROKER_URL = ""  # 'redis://localhost:6380'
CELERY_RESULT_BACKEND = ""  # 'redis://localhost:6380'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = False

CELERY_BEAT_SCHEDULE = {
    'task-check-jobs': {
        'task': 'exports.tasks.check_jobs',
        'schedule': 60,
    },
    'task-clean-jobs': {
        'task': 'exports.tasks.clean_jobs',
        'schedule': 3600,
    },
}

# CONSTANTS
utc = pytz.UTC

MANUAL_SOURCE = "Manual"
PERIMETERS_TYPES = ["AP-HP", "Hospital group", "Hospital"]
ROOT_PERIMETER_TYPE = PERIMETERS_TYPES[0]
SHARED_FOLDER_NAME = 'Mes requêtes reçues'
MODEL_MANUAL_START_DATE_DEFAULT_ON_UPDATE = utc.localize(datetime.combine(
    date(1970, 1, 1), time.min))
MODEL_MANUAL_END_DATE_DEFAULT_ON_UPDATE = utc.localize(datetime.combine(
    date(2070, 1, 1), time.min))

JWT_SESSION_COOKIE = "access"
JWT_REFRESH_COOKIE = "refresh"


# WORKSPACES
if 'workspaces' in INCLUDED_APPS:
    RANGER_HIVE_POLICY_TYPES = ["type1", "type2"]
