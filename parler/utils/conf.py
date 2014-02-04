from django.conf import settings
from django.utils.translation import get_language



class LanguagesSetting(dict):
    """
    The languages settings dictionary, with extra methods attached.
    """

    def get_language(self, language_code, site_id=None):
        """
        Return the language settings for the current site

        This function can be used with other settings variables
        to support modules which create their own variation of the ``PARLER_LANGUAGES`` setting.
        For an example, see :func:`~parler.appsettings.add_default_language_settings`.
        """
        if site_id is None:
            site_id = settings.SITE_ID

        for lang_dict in self.get(site_id, ()):
            if lang_dict['code'] == language_code:
                return lang_dict

        return self['default']


    def get_active_choices(self, language_code=None):
        """
        Find out which translations should be visible in the site.
        It returns a tuple with either a single choice (the current language),
        or a tuple with the current language + fallback language.
        """
        if language_code is None:
            language_code = get_language()

        lang_dict = self.get_language(language_code)
        if not lang_dict['hide_untranslated'] and lang_dict['fallback'] != language_code:
            return (language_code, lang_dict['fallback'])
        else:
            return (language_code,)


    def get_fallback_language(self, language_code=None):
        """
        Find out what the fallback language is for a given language choice.
        """
        choices = self.get_active_choices(language_code)
        if choices and len(choices) > 1:
            return choices[-1]
        else:
            return None
