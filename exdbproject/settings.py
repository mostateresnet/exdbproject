"""
Django settings for exdbproject project.

Generated by 'django-admin startproject' using Django 1.9a1.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import os
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

# register checks
import exdbproject.checks


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

BAD_SECRET_KEY = 'poor-key'
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = BAD_SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'exdb',
]

RESTRICTED_ACCESS_MIDDLEWARE = 'exdb.restricted_access_middleware.RestrictedAccess'

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    RESTRICTED_ACCESS_MIDDLEWARE,
]

ROOT_URLCONF = 'exdbproject.urls'

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

WSGI_APPLICATION = 'exdbproject.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'

# override the default test runner
TEST_RUNNER = 'exdb.tests.CustomRunner'

# excludes directories with these names from being included in linting
JS_FILE_EXCLUDED_DIRS = ['coverage', 'instrumented_static', 'libraries', 'htmlcov']
PY_FILE_EXCLUDED_DIRS = ['migrations']

# restricted access middleware permissions
# a dictionary of functions which determine whether a user has access
# the functions return True if the user has permission
# the functions will be passed a request object
PERMS_AND_LEVELS = {
    'basic': lambda x: True,
}

LOGIN_REDIRECT_URL = 'home'

LOGIN_URL = 'login'

# Use augmented user model
AUTH_USER_MODEL = 'exdb.EXDBUser'

HALLSTAFF_TIME_AHEAD = timezone.timedelta(days=7)
RA_TIME_AHEAD = timezone.timedelta(days=31)

# override settings with settings_local
try:
    from exdbproject.settings_local import *  # pylint: disable=wildcard-import,unused-wildcard-import,wrong-import-position
except ImportError:
    pass
