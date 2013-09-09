"""
Overview of all settings which can be customized.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from parler.utils import normalize_language_code, is_supported_django_language

PARLER_DEFAULT_LANGUAGE_CODE = getattr(settings, 'PARLER_DEFAULT_LANGUAGE_CODE', settings.LANGUAGE_CODE)

PARLER_SHOW_EXCLUDED_LANGUAGE_TABS = getattr(settings, 'PARLER_SHOW_EXCLUDED_LANGUAGE_TABS', False)

PARLER_LANGUAGES = getattr(settings, 'PARLER_LANGUAGES', {})


# Clean settings
PARLER_DEFAULT_LANGUAGE_CODE = normalize_language_code(PARLER_DEFAULT_LANGUAGE_CODE)

def _clean_languages():
    if not is_supported_django_language(PARLER_DEFAULT_LANGUAGE_CODE):
        raise ImproperlyConfigured("PARLER_DEFAULT_LANGUAGE_CODE '{0}' does not exist in LANGUAGES".format(PARLER_DEFAULT_LANGUAGE_CODE))

    PARLER_LANGUAGES.setdefault('default', {})
    defaults = PARLER_LANGUAGES['default']
    defaults.setdefault('code', PARLER_DEFAULT_LANGUAGE_CODE)
    defaults.setdefault('fallback', PARLER_DEFAULT_LANGUAGE_CODE)

    for site_id, lang_choices in PARLER_LANGUAGES.iteritems():
        if site_id == 'default':
            continue

        if not isinstance(lang_choices, (list, tuple)):
            raise ImproperlyConfigured("PARLER_LANGUAGES[{0}] should be a tuple of language choices!".format(site_id))
        for i, choice in enumerate(lang_choices):
            if not is_supported_django_language(choice['code']):
                raise ImproperlyConfigured("PARLER_LANGUAGES[{0}][{1}]['code'] does not exist in LANGUAGES".format(site_id, i))

            # Copy all items from the defaults, so you can provide new fields too.
            for key, value in defaults.iteritems():
                choice.setdefault(key, value)

_clean_languages()
