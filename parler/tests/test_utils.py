# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.test import TestCase

from parler.utils import get_parler_languages_from_django_cms


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
