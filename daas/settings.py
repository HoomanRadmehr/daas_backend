"""
Django settings for daas project.

Generated by 'django-admin startproject' using Django 4.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
from django.utils.translation import gettext_lazy as _
from celery.schedules import crontab
from dotenv import load_dotenv
from datetime import timedelta
import os

MODE=os.getenv("DAAS_MODE")
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-)d$_9ds!es2@bhz3ht7n_^*_dqw!ke4n@5d&11ila-d8v+fkc_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "*",
    "192.168.2.21"
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #third_party
    'rest_framework',
    'django_filters',
    'corsheaders',
    "django_celery_beat",
    'rest_framework_simplejwt.token_blacklist',
    #apps
    'config.apps.ConfigConfig',
    'users.apps.UsersConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = 'daas.urls'

CORS_ALLOW_ALL_ORIGINS=True

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend']
}


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'daas.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {

    'default': {

        'ENGINE': 'django.db.backends.postgresql_psycopg2',

        'NAME': os.getenv("DAAS_POSTGRES_NAME"),

        'USER': os.getenv("DAAS_POSTGRES_USER"),

        'PASSWORD': os.getenv("DAAS_POSTGRES_PASSWORD"),

        'HOST': os.getenv("DAAS_POSTGRES_HOST"),

        'PORT': os.getenv("DAAS_POSTGRES_PORT"),

    }

}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR,"static")
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR,"media")

LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('fa', _('Farsi')),
    ('en', _('English')),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

USE_I18N = True

USE_L10N = True

#celery beat

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES':{
        'login':'3/minute'
    }
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=10),
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
AUTH_USER_MODEL = 'users.Users'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CELERY_PERIODIC_TASK_TIME = int(os.getenv("CELERY_PERIODIC_TASK_TIME"))
CELERY_BROKER_URL = os.getenv("CELRY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
CELERY_TIME_ZONE = "Asia/Tehran"
CELERY_BEAT_SCHEDULE = { 
    'stop_unused_container' : {  
        'task': 'users.tasks.stop_unused_container', 
        'schedule': timedelta(minutes=1), 
    },
    'time_restriction_checker' : {  
        'task': 'users.tasks.time_restriction_checker', 
        'schedule': timedelta(minutes=1), 
    },
    'reset_daases_usage' : {  
        'task': 'users.tasks.reset_daases_usage', 
        'schedule': crontab(minute='0',hour='0'), 
    },
}

FILE_SERVER_HOST = os.getenv("FILE_SERVER_HOST")
MANEGER_HOST = os.getenv("MANEGER_HOST")

TIME_ZONE = 'Asia/Tehran'

if MODE:
    if MODE.lower()=="production" or MODE.lower()=='prod':
        DEBUG=False
        from django.core.management.utils import get_random_secret_key
        SECRET_KEY=get_random_secret_key()
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
        # SECURE_SSL_REDIRECT = False
        # SESSION_COOKIE_SECURE = False
        # CSRF_COOKIE_SECURE = False
        