from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.contrib.sites.models import Site
from django.db.models import loading
from django.template.loaders import app_directories
from django.test import TestCase
from django.utils.importlib import import_module
import os


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
        if cls.install_apps:
            # When running this app via `./manage.py test fluent_pages`, auto install the test app + models.
            run_syncdb = False
            for appname in cls.install_apps:
                if appname not in settings.INSTALLED_APPS:
                    print 'Adding {0} to INSTALLED_APPS'.format(appname)
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
