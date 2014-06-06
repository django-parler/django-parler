#!/usr/bin/env python
import sys
from django.conf import settings, global_settings as default_settings
from django.core.management import execute_from_command_line
from os import path

if not settings.configured:
    module_root = path.dirname(path.realpath(__file__))

    settings.configure(
        DEBUG = False,  # will be False anyway by DjangoTestRunner.
        TEMPLATE_DEBUG = True,
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        },
        TEMPLATE_LOADERS = (
            'django.template.loaders.app_directories.Loader',
        ),
        TEMPLATE_CONTEXT_PROCESSORS = default_settings.TEMPLATE_CONTEXT_PROCESSORS + (
            'django.core.context_processors.request',
        ),
        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sites',
            'django.contrib.admin',
            'django.contrib.sessions',
            'parler',
            'parler.tests.testapp',
        ),
        ROOT_URLCONF = 'parler.tests.testapp.urls',
        TEST_RUNNER='django.test.simple.DjangoTestSuiteRunner',   # for Django 1.6, see https://docs.djangoproject.com/en/dev/releases/1.6/#new-test-runner

        SITE_ID = 4,
        LANGUAGE_CODE = 'en',
        PARLER_LANGUAGES = {
            4: (
                {'code': 'nl'},
                {'code': 'de'},
                {'code': 'en'},
            ),
            'default': {
                'fallback': 'en',
            },
        },
    )

def runtests():
    argv = sys.argv[:1] + ['test', 'parler'] + sys.argv[1:]
    execute_from_command_line(argv)

if __name__ == '__main__':
    runtests()
