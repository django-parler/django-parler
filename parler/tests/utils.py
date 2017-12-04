from __future__ import print_function
import os

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.utils import override_settings
from importlib import import_module

from parler import appsettings

User = get_user_model()


def clear_cache():
    """
    Clear internal cache of apps loading
    """
    apps.clear_cache()


class override_parler_settings(override_settings):
    """
    Make sure the parler.appsettings is also updated with override_settings()
    """

    def __init__(self, **kwargs):
        super(override_parler_settings, self).__init__(**kwargs)
        self.old_values = {}

    def enable(self):
        super(override_parler_settings, self).enable()
        for key, value in self.options.items():
            self.old_values[key] = getattr(appsettings, key)
            setattr(appsettings, key, value)

    def disable(self):
        super(override_parler_settings, self).disable()
        for key in self.options.keys():
            setattr(appsettings, key, self.old_values[key])


class AppTestCase(TestCase):
    """
    Tests for URL resolving.
    """
    user = None
    install_apps = (
        'parler.tests.testapp',
    )

    def setUp(self):
        super(AppTestCase, self).setUp()
        cache.clear()

    @classmethod
    def setUpClass(cls):
        super(AppTestCase, cls).setUpClass()

        from django.template.loaders import app_directories  # late import, for django 1.7
        if cls.install_apps:
            # When running this app via `./manage.py test fluent_pages`, auto install the test app + models.
            run_syncdb = False
            for appname in cls.install_apps:
                if appname not in settings.INSTALLED_APPS:
                    print('Adding {0} to INSTALLED_APPS'.format(appname))
                    settings.INSTALLED_APPS = (appname,) + tuple(settings.INSTALLED_APPS)
                    run_syncdb = True

                    # Flush caches
                    testapp = import_module(appname)
                    clear_cache()
                    app_directories.app_template_dirs += (
                        os.path.join(os.path.dirname(testapp.__file__), 'templates'),
                    )

            if run_syncdb:
                call_command('syncdb', verbosity=0)  # may run south's overlaid version

        # Create basic objects
        # Django does not create site automatically with the defined SITE_ID
        Site.objects.get_or_create(id=settings.SITE_ID, defaults=dict(domain='django.localhost', name='django at localhost'))
        cls.user, _ = User.objects.get_or_create(is_superuser=True, is_staff=True, username="admin")

        # Be supportive for other project settings too.
        cls.conf_fallbacks = list(appsettings.PARLER_LANGUAGES['default']['fallbacks'] or ['en'])
        cls.conf_fallback = cls.conf_fallbacks[0]
        cls.other_lang1 = next(x for x, _ in settings.LANGUAGES if x not in cls.conf_fallbacks)  # "af"
        cls.other_lang2 = next(x for x, _ in settings.LANGUAGES if x not in cls.conf_fallbacks + [cls.other_lang1])  # "ar"
