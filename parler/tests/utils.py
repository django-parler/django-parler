from __future__ import print_function
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.contrib.sites.models import Site
from django.db.models import loading
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.importlib import import_module
import os
from parler import appsettings


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


    @classmethod
    def setUpClass(cls):
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
                    loading.cache.loaded = False
                    app_directories.app_template_dirs += (
                        os.path.join(os.path.dirname(testapp.__file__), 'templates'),
                    )

            if run_syncdb:
                call_command('syncdb', verbosity=0)  # may run south's overlaid version

        # Create basic objects
        # 1.4 does not create site automatically with the defined SITE_ID, 1.3 does.
        Site.objects.get_or_create(id=settings.SITE_ID, defaults=dict(domain='django.localhost', name='django at localhost'))
        cls.user, _ = User.objects.get_or_create(is_superuser=True, is_staff=True, username="admin")

        # Be supportive for other project settings too.
        cls.conf_fallback = appsettings.PARLER_LANGUAGES['default']['fallback'] or 'en'
        cls.other_lang1 = next(x for x, _ in settings.LANGUAGES if x != cls.conf_fallback)
        cls.other_lang2 = next(x for x, _ in settings.LANGUAGES if x not in (cls.conf_fallback, cls.other_lang1))
