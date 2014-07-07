"""
The configuration wrappers that are used for :ref:`PARLER_LANGUAGES`.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.translation import get_language
from parler.utils.i18n import is_supported_django_language


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

    :param languages_list: The settings, in :ref:`PARLER_LANGUAGES` format.
    :param var_name: The name of your variable, for debugging output.
    :param extra_defaults: Any defaults to override in the ``languages_list['default']`` section, e.g. ``code``, ``fallback``, ``hide_untranslated``.
    :return: The updated ``languages_list`` with all defaults applied to all sections.
    :rtype: LanguagesSetting
    """
    languages_list = LanguagesSetting(languages_list)

    languages_list.setdefault('default', {})
    defaults = languages_list['default']
    defaults.setdefault('hide_untranslated', False)   # Whether queries with .active_translations() may or may not return the fallback language.
    defaults.update(extra_defaults)  # Also allow to override code and fallback this way.

    # This function previously existed in appsettings, where it could reference the defaults directly.
    # However, this module is a more logical place for this function. To avoid circular import problems,
    # the 'code' and 'fallback' parameters are always passed by the appsettings module.
    # In case these are missing, default to the original behavior for backwards compatibility.
    if 'code' not in defaults:
        from parler import appsettings
        defaults['code'] = appsettings.PARLER_DEFAULT_LANGUAGE_CODE
    if 'fallback' not in defaults:
        from parler import appsettings
        defaults['fallback'] = appsettings.PARLER_DEFAULT_LANGUAGE_CODE

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



class LanguagesSetting(dict):
    """
    This is the actual object type of the :ref:`PARLER_LANGUAGES` setting.
    Besides the regular :class:`dict` behavior, it also adds some additional methods.
    """

    def get_language(self, language_code, site_id=None):
        """
        Return the language settings for the current site

        This function can be used with other settings variables
        to support modules which create their own variation of the ``PARLER_LANGUAGES`` setting.
        For an example, see :func:`~parler.appsettings.add_default_language_settings`.
        """
        if site_id is None:
            site_id = getattr(settings, 'SITE_ID', None)

        for lang_dict in self.get(site_id, ()):
            if lang_dict['code'] == language_code:
                return lang_dict

        return self['default']


    def get_active_choices(self, language_code=None, site_id=None):
        """
        Find out which translations should be visible in the site.
        It returns a tuple with either a single choice (the current language),
        or a tuple with the current language + fallback language.
        """
        if language_code is None:
            language_code = get_language()

        lang_dict = self.get_language(language_code, site_id=site_id)
        if not lang_dict['hide_untranslated'] and lang_dict['fallback'] != language_code:
            return (language_code, lang_dict['fallback'])
        else:
            return (language_code,)


    def get_fallback_language(self, language_code=None, site_id=None):
        """
        Find out what the fallback language is for a given language choice.
        """
        choices = self.get_active_choices(language_code, site_id=site_id)
        if choices and len(choices) > 1:
            return choices[-1]
        else:
            return None


    def get_default_language(self):
        """
        Return the default language.
        """
        return self['default']['code']


    def get_first_language(self, site_id=None):
        """
        Return the first language for the current site.
        This can be used for user interfaces, where the languages are displayed in tabs.
        """
        if site_id is None:
            site_id = getattr(settings, 'SITE_ID', None)

        try:
            return self[site_id][0]['code']
        except (KeyError, IndexError):
            # No configuration, always fallback to default language.
            # This is essentially a non-multilingual configuration.
            return self['default']['code']
