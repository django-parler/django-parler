# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import django
from django.test import TestCase
from django.utils.translation import override

from parler.templatetags.parler_tags import _url_qs
from parler.tests.utils import override_parler_settings
from parler.utils import get_parler_languages_from_django_cms
from parler.utils.i18n import get_language, get_language_title


class UtilTestCase(TestCase):

    def test_get_parler_languages_from_django_cms(self):
        cms = {
            1: [
                {
                    'code': 'en',
                    'fallbacks': ['es'],
                    'hide_untranslated': True,
                    'name': 'English',
                    'public': True,
                    'redirect_on_fallback': True
                },
                {
                    'code': 'es',
                    'fallbacks': ['en'],
                    'hide_untranslated': True,
                    'name': 'Spanish',
                    'public': True,
                    'redirect_on_fallback': True
                },
                {
                    'code': 'fr',
                    'fallbacks': ['en'],
                    'hide_untranslated': True,
                    'name': 'French',
                    'public': True,
                    'redirect_on_fallback': True
                }
            ],
            'default': {
                'fallbacks': ['en', ],
                'hide_untranslated': True,
                'public': True,
                'redirect_on_fallback': True
            }
        }

        parler = {
            1: [
                {
                    'code': 'en',
                    'fallbacks': ['es'],
                    'hide_untranslated': True,
                    'redirect_on_fallback': True
                },
                {
                    'code': 'es',
                    'fallbacks': ['en'],
                    'hide_untranslated': True,
                    'redirect_on_fallback': True
                },
                {
                    'code': 'fr',
                    'fallbacks': ['en'],
                    'hide_untranslated': True,
                    'redirect_on_fallback': True
                }
            ],
            'default': {
                'fallbacks': ['en', ],
                'hide_untranslated': True,
                'redirect_on_fallback': True
            }
        }

        computed = get_parler_languages_from_django_cms(cms)
        for block, block_config in computed.items():
            self.assertEqual(computed[block], parler[block])

    def test_get_language_title(self):
        """Test get_language_title utility function"""
        language_code = 'en'
        self.assertEqual(get_language_title(language_code), 'English')

        # Test the case where requested language is not in settings.
        # We can not override settings, since languages in get_language_title()
        # are initialised during import. So, we use fictional language code.
        language_code = 'xx'
        try:
            self.assertEqual(get_language_title(language_code), language_code)
        except KeyError:
            self.fail(
                "get_language_title() raises KeyError for missing language")

    @override_parler_settings(PARLER_DEFAULT_ACTIVATE=False)
    def test_get_language_no_fallback(self):
        """Test get_language patch function, no fallback"""

        with override(None):
            if django.VERSION >= (1, 8):
                self.assertEquals(get_language(), None)

    @override_parler_settings(PARLER_DEFAULT_ACTIVATE=True)
    def test_get_language_with_fallback(self):
        """Test get_language patch function, with fallback"""
        from parler import appsettings

        with override(None):
            if django.VERSION >= (1, 8):
                self.assertEquals(get_language(), appsettings.PARLER_DEFAULT_LANGUAGE_CODE)

    def test_url_qs(self):
        matches = [
            ('http://www.example.com/search/', 'q=è453è5p4j5uih758'),
            (u'http://www.example.com/search/', b'next=/fr/propri\xc3\xa9t\xc3\xa9/'),
        ]
        for match in matches:
            merged = _url_qs(match[0], match[1])
            self.assertTrue(merged)
