"""
Overview of all settings which can be customized.
"""
from django.conf import settings
from parler.utils import normalize_language_code
from parler.utils.conf import add_default_language_settings


PARLER_DEFAULT_LANGUAGE_CODE = getattr(settings, 'PARLER_DEFAULT_LANGUAGE_CODE', settings.LANGUAGE_CODE)

PARLER_SHOW_EXCLUDED_LANGUAGE_TABS = getattr(settings, 'PARLER_SHOW_EXCLUDED_LANGUAGE_TABS', False)

PARLER_LANGUAGES = getattr(settings, 'PARLER_LANGUAGES', {})

PARLER_ENABLE_CACHING = getattr(settings, 'PARLER_ENABLE_CACHING', True)

# Have to fill the default section explicitly to avoid circular imports
PARLER_LANGUAGES.setdefault('default', {})
PARLER_LANGUAGES['default'].setdefault('code', PARLER_DEFAULT_LANGUAGE_CODE)
PARLER_LANGUAGES['default'].setdefault('fallback', PARLER_DEFAULT_LANGUAGE_CODE)

# Cleanup settings
PARLER_DEFAULT_LANGUAGE_CODE = normalize_language_code(PARLER_DEFAULT_LANGUAGE_CODE)
PARLER_LANGUAGES = add_default_language_settings(PARLER_LANGUAGES)
