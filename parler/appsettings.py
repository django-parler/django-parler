"""
Overview of all settings which can be customized.
"""
from django.conf import settings

from parler.utils import get_parler_languages_from_django_cms, normalize_language_code
from parler.utils.conf import add_default_language_settings

PARLER_DEFAULT_LANGUAGE_CODE = getattr(
    settings, "PARLER_DEFAULT_LANGUAGE_CODE", settings.LANGUAGE_CODE
)

PARLER_SHOW_EXCLUDED_LANGUAGE_TABS = getattr(settings, "PARLER_SHOW_EXCLUDED_LANGUAGE_TABS", False)

PARLER_LANGUAGES = getattr(settings, "PARLER_LANGUAGES", {})

if not PARLER_LANGUAGES:
    if hasattr(settings, "CMS_LANGUAGES"):
        PARLER_LANGUAGES = get_parler_languages_from_django_cms(getattr(settings, "CMS_LANGUAGES"))

PARLER_ENABLE_CACHING = getattr(settings, "PARLER_ENABLE_CACHING", True)

# Prefix for sites that share the same cache. For example Aldryn News & Blog.
PARLER_CACHE_PREFIX = getattr(settings, "PARLER_CACHE_PREFIX", "")

# Have to fill the default section explicitly to avoid circular imports
PARLER_LANGUAGES.setdefault("default", {})
PARLER_LANGUAGES["default"].setdefault("code", PARLER_DEFAULT_LANGUAGE_CODE)
PARLER_LANGUAGES["default"].setdefault("fallbacks", [PARLER_DEFAULT_LANGUAGE_CODE])

# Cleanup settings
PARLER_DEFAULT_LANGUAGE_CODE = normalize_language_code(PARLER_DEFAULT_LANGUAGE_CODE)
PARLER_LANGUAGES = add_default_language_settings(PARLER_LANGUAGES)

# Activate translations by default. Flag to compensate for Django >= 1.8 default `get_language` behavior
PARLER_DEFAULT_ACTIVATE = getattr(settings, "PARLER_DEFAULT_ACTIVATE", False)
