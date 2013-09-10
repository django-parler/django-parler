"""
Utils for translations
"""
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

LANGUAGES_DICT = dict(settings.LANGUAGES)


def normalize_language_code(code):
    """
    Undo the differences between language code notations
    """
    return code.lower().replace('_', '-')


def is_supported_django_language(language_code):
    """
    Return whether a language code is supported.
    """
    language_code = language_code.split('-')[0] # e.g. if fr-ca is not supported fallback to fr
    return language_code in LANGUAGES_DICT


def get_language_title(language_code):
    """
    Return the verbose_name for a language code.
    """
    try:
        return _(LANGUAGES_DICT[language_code])
    except KeyError:
        language_code = language_code.split('-')[0] # e.g. if fr-ca is not supported fallback to fr
        return _(LANGUAGES_DICT[language_code])


def get_language_settings(language_code, site_id=None):
    """
    Return the language settings for the current site
    """
    from parler import appsettings
    if site_id is None:
        site_id = settings.SITE_ID

    for lang_dict in appsettings.PARLER_LANGUAGES.get(site_id, ()):
        if lang_dict['code'] == language_code:
            return lang_dict

    return appsettings.PARLER_LANGUAGES['default']


def is_multilingual_project(site_id=None):
    """
    Whether the current Django project is configured for multilingual support.
    """
    from parler import appsettings
    return appsettings.PARLER_SHOW_EXCLUDED_LANGUAGE_TABS or appsettings.PARLER_LANGUAGES.has_key(site_id or settings.SITE_ID)
