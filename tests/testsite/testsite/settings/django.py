"""
Django default settings, customised as necessary for testing.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = "fake-secret-key-for-testing"

DEBUG = True

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "devdata",
    "polls",
    "photofeed",
    "turtles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "testsite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "testsite.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # We need the same database name in both normal running from `manage.py`
        # and pytest-django's test environment. This means we call the database
        # "devdata" here, but it's "test_devdata" in pytest, and we override the
        # environment to set "test_devdata" when calling from tests.
        "NAME": os.environ.get("TEST_DATABASE_NAME", "devdata"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Overrides for CI/testing. Not used by default because local development
# doesn't typically need these.

if "POSTGRES_USER" in os.environ:
    DATABASES["default"]["USER"] = os.environ["POSTGRES_USER"]

if "POSTGRES_PASSWORD" in os.environ:
    DATABASES["default"]["PASSWORD"] = os.environ["POSTGRES_PASSWORD"]

if "POSTGRES_HOST" in os.environ:
    DATABASES["default"]["HOST"] = os.environ["POSTGRES_HOST"]

if "POSTGRES_PORT" in os.environ:
    DATABASES["default"]["PORT"] = os.environ["POSTGRES_PORT"]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = "/static/"
