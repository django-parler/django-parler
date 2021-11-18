#!/usr/bin/env python
import sys
from os import path

import django
from django.conf import global_settings as default_settings
from django.conf import settings
from django.core.management import execute_from_command_line

# Give feedback on used versions
sys.stderr.write("Using Python version {0} from {1}\n".format(sys.version[:5], sys.executable))
sys.stderr.write(
    "Using Django version {0} from {1}\n".format(
        django.get_version(), path.dirname(path.abspath(django.__file__))
    )
)

if not settings.configured:
    module_root = path.dirname(path.realpath(__file__))
    sys.path.insert(0, path.join(module_root, "example"))

    settings.configure(
        DEBUG=False,  # will be False anyway by DjangoTestRunner.
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        CACHES={
            # By explicit since many tests also need the caching support
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "unique-snowflake",
            }
        },
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.messages",
            "django.contrib.sessions",
            "django.contrib.sites",
            "django.contrib.admin",
            "parler",
            "parler.tests.testapp",
            "article",
            "theme1",
        ),
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": (),
                "OPTIONS": {
                    "loaders": (
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ),
                    "context_processors": (
                        "django.template.context_processors.debug",
                        "django.template.context_processors.i18n",
                        "django.template.context_processors.media",
                        "django.template.context_processors.request",
                        "django.template.context_processors.static",
                        "django.contrib.messages.context_processors.messages",
                        "django.contrib.auth.context_processors.auth",
                    ),
                },
            },
        ],
        MIDDLEWARE=(
            "django.middleware.common.CommonMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.locale.LocaleMiddleware",  # / will be redirected to /<locale>/
        ),
        ROOT_URLCONF="example.urls",
        TEST_RUNNER="django.test.runner.DiscoverRunner",
        SECRET_KEY="secret",
        SITE_ID=4,
        LANGUAGE_CODE="en",
        LANGUAGES=(
            ("nl", "Dutch"),
            ("de", "German"),
            ("en", "English"),
            ("fr", "French"),
        ),
        PARLER_LANGUAGES={
            4: (
                {"code": "nl"},
                {"code": "de"},
                {"code": "en"},
            ),
            "default": {
                "fallbacks": ["en"],
            },
        },
    )


DEFAULT_TEST_APPS = [
    "parler",
    "article",
]


def runtests():
    other_args = list(filter(lambda arg: arg.startswith("-"), sys.argv[1:]))
    test_apps = (
        list(filter(lambda arg: not arg.startswith("-"), sys.argv[1:])) or DEFAULT_TEST_APPS
    )
    argv = sys.argv[:1] + ["test", "--traceback"] + other_args + test_apps
    execute_from_command_line(argv)


if __name__ == "__main__":
    runtests()
