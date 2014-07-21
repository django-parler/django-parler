.. _custom-language-settings:

Customizing language settings
=============================

If needed, projects can "fork" the parler language settings.
This is rarely needed. Example::

    from django.conf import settings
    from parler import appsettings as parler_appsettings
    from parler.utils import normalize_language_code, is_supported_django_language
    from parler.utils.conf import add_default_language_settings

    MYCMS_DEFAULT_LANGUAGE_CODE = getattr(settings, 'MYCMS_DEFAULT_LANGUAGE_CODE', FLUENT_DEFAULT_LANGUAGE_CODE)
    MYCMS_LANGUAGES = getattr(settings, 'MYCMS_LANGUAGES', parler_appsettings.PARLER_LANGUAGES)

    MYCMS_DEFAULT_LANGUAGE_CODE = normalize_language_code(MYCMS_DEFAULT_LANGUAGE_CODE)

    MYCMS_LANGUAGES = add_default_language_settings(
        MYCMS_LANGUAGES, 'MYCMS_LANGUAGES',
        hide_untranslated=False,
        hide_untranslated_menu_items=False,
        code=MYCMS_DEFAULT_LANGUAGE_CODE,
        fallback=MYCMS_DEFAULT_LANGUAGE_CODE
    )

Instead of using the functions from :mod:`parler.utils` (such as :func:`~parler.utils.get_active_language_choices`)
the project can access the language settings using::

    MYCMS_LANGUAGES.get_language()
    MYCMS_LANGUAGES.get_active_choices()
    MYCMS_LANGUAGES.get_fallback_language()
    MYCMS_LANGUAGES.get_default_language()
    MYCMS_LANGUAGES.get_first_language()

These methods are added by the :func:`~parler.utils.conf.add_default_language_settings` function.
See the :class:`~parler.utils.conf.LanguagesSetting` class for details.
