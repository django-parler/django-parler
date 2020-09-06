"""
Utils for translations
"""
from django.conf import settings
from django.conf.global_settings import LANGUAGES as ALL_LANGUAGES
from django.utils.translation import gettext_lazy as _, get_language as dj_get_language


__all__ = (
    'normalize_language_code',
    'is_supported_django_language',
    'get_language_title',
    'get_language_settings',
    'get_active_language_choices',
    'is_multilingual_project',
)


LANGUAGES_DICT = dict(settings.LANGUAGES)
ALL_LANGUAGES_DICT = dict(ALL_LANGUAGES)

# allow to override language names when  PARLER_SHOW_EXCLUDED_LANGUAGE_TABS is True:
ALL_LANGUAGES_DICT.update(LANGUAGES_DICT)


def normalize_language_code(code):
    """
    Undo the differences between language code notations
    """
    if code is None:
        return None
    else:
        return code.lower().replace('_', '-')


def is_supported_django_language(language_code):
    """
    Return whether a language code is supported.
    """
    language_code2 = language_code.split('-')[0] # e.g. if fr-ca is not supported fallback to fr
    return language_code in LANGUAGES_DICT or language_code2 in LANGUAGES_DICT


def get_language_title(language_code):
    """
    Return the verbose_name for a language code.

    Fallback to language_code if language is not found in settings.
    """
    from parler import appsettings
    # Avoid weird lookup errors.
    if not language_code:
        raise ValueError("Missing language_code in get_language_title()")

    if appsettings.PARLER_SHOW_EXCLUDED_LANGUAGE_TABS:
        # this allows to edit languages that are not enabled in current project but are already
        # in database
        languages = ALL_LANGUAGES_DICT
    else:
        languages = LANGUAGES_DICT

    try:
        return _(languages[language_code])
    except KeyError:
        language_code = language_code.split('-')[0]  # e.g. if fr-ca is not supported fallback to fr
        language_title = languages.get(language_code, None)
        if language_title is not None:
            return _(language_title)
        else:
            return language_code


def get_language_settings(language_code, site_id=None):
    """
    Return the language settings for the current site
    """
    # This method mainly exists for ease-of-use.
    # the body is part of the settings, to allow third party packages
    # to have their own variation of the settings with this method functionality included.
    from parler import appsettings
    return appsettings.PARLER_LANGUAGES.get_language(language_code, site_id)


def get_active_language_choices(language_code=None):
    """
    Find out which translations should be visible in the site.
    It returns a tuple with either a single choice (the current language),
    or a tuple with the current language + fallback language.
    """
    from parler import appsettings
    return appsettings.PARLER_LANGUAGES.get_active_choices(language_code)


def is_multilingual_project(site_id=None):
    """
    Whether the current Django project is configured for multilingual support.
    """
    from parler import appsettings
    if site_id is None:
        site_id = getattr(settings, 'SITE_ID', None)
    return appsettings.PARLER_SHOW_EXCLUDED_LANGUAGE_TABS or site_id in appsettings.PARLER_LANGUAGES


def get_null_language_error():
    # Internal util to get the language error
    if get_language() is None:
        # This happens when using parler in management commands.
        # Use translation.activate('en') if you need to have a default locale active.
        return "language_code can't be null, use translation.activate(..) when accessing translated models outside the request/response loop."
    else:
        return "language_code can't be null"


def get_language():
    """
    Wrapper around Django's `get_language` utility.
    For Django >= 1.8, `get_language` returns None in case no translation is activate.
    Here we patch this behavior e.g. for back-end functionality requiring access to translated fields
    """
    from parler import appsettings
    language = dj_get_language()
    if language is None and appsettings.PARLER_DEFAULT_ACTIVATE:
        return appsettings.PARLER_DEFAULT_LANGUAGE_CODE
    else:
        return language
