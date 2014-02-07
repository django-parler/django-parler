"""
Overview of all settings which can be customized.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from parler.utils import normalize_language_code, is_supported_django_language
from parler.utils.conf import LanguagesSetting

PARLER_DEFAULT_LANGUAGE_CODE = getattr(settings, 'PARLER_DEFAULT_LANGUAGE_CODE', settings.LANGUAGE_CODE)

PARLER_SHOW_EXCLUDED_LANGUAGE_TABS = getattr(settings, 'PARLER_SHOW_EXCLUDED_LANGUAGE_TABS', False)

PARLER_LANGUAGES = getattr(settings, 'PARLER_LANGUAGES', {})

PARLER_ENABLE_CACHING = getattr(settings, 'PARLER_ENABLE_CACHING', True)


def add_default_language_settings(languages_list, var_name='PARLER_LANGUAGES', **extra_defaults):
    """
    Apply extra defaults to the language settings.
    This function can also be used by other packages to
    create their own variation of ``PARLER_LANGUAGES`` with extra fields.
    For example::

        from django.conf import settings
        from parler import appsettings as parler_appsettings

        # Create local names, which are based on the global parler settings
        MYAPP_DEFAULT_LANGUAGE_CODE = getattr(settings, 'MYAPP_DEFAULT_LANGUAGE_CODE', parler_appsettings.PARLER_DEFAULT_LANGUAGE_CODE)
        MYAPP_LANGUAGES = getattr(settings, 'MYAPP_LANGUAGES', parler_appsettings.PARLER_LANGUAGES)

        # Apply the defaults to the languages
        MYAPP_LANGUAGES = parler_appsettings.add_default_language_settings(MYAPP_LANGUAGES, 'MYAPP_LANGUAGES',
            code=MYAPP_DEFAULT_LANGUAGE_CODE,
            fallback=MYAPP_DEFAULT_LANGUAGE_CODE,
            hide_untranslated=False
        )

    The returned object will be an :class:`~parler.utils.conf.LanguagesSetting` object,
    which adds additional methods to the :class:`dict` object.
    """
    languages_list = LanguagesSetting(languages_list)

    languages_list.setdefault('default', {})
    defaults = languages_list['default']
    defaults.setdefault('code', PARLER_DEFAULT_LANGUAGE_CODE)
    defaults.setdefault('fallback', PARLER_DEFAULT_LANGUAGE_CODE)
    defaults.setdefault('hide_untranslated', False)   # Whether queries with .active_translations() may or may not return the fallback language.
    defaults.update(extra_defaults)  # Also allow to override code and fallback this way.

    if not is_supported_django_language(defaults['code']):
        raise ImproperlyConfigured("The value for {0}['defaults']['code'] ('{1}') does not exist in LANGUAGES".format(var_name, defaults['code']))

    for site_id, lang_choices in six.iteritems(languages_list):
        if site_id == 'default':
            continue

        if not isinstance(lang_choices, (list, tuple)):
            raise ImproperlyConfigured("{0}[{1}] should be a tuple of language choices!".format(var_name, site_id))
        for i, choice in enumerate(lang_choices):
            if not is_supported_django_language(choice['code']):
                raise ImproperlyConfigured("{0}[{1}][{2}]['code'] does not exist in LANGUAGES".format(var_name, site_id, i))

            # Copy all items from the defaults, so you can provide new fields too.
            for key, value in six.iteritems(defaults):
                choice.setdefault(key, value)

    return languages_list


# Clean settings
PARLER_DEFAULT_LANGUAGE_CODE = normalize_language_code(PARLER_DEFAULT_LANGUAGE_CODE)
PARLER_LANGUAGES = add_default_language_settings(PARLER_LANGUAGES)
