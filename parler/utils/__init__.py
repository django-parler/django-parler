"""
Utility functions to handle language codes and settings.
"""

from .conf import get_parler_languages_from_django_cms
from .i18n import (
    get_active_language_choices,
    get_language_settings,
    get_language_title,
    is_multilingual_project,
    is_supported_django_language,
    normalize_language_code,
)

__all__ = (
    "normalize_language_code",
    "is_supported_django_language",
    "get_language_title",
    "get_language_settings",
    "get_active_language_choices",
    "is_multilingual_project",
)
