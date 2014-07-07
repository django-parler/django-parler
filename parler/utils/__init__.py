"""
Utility functions to handle language codes and settings.
"""

from .i18n import (
    normalize_language_code,
    is_supported_django_language,
    get_language_title,
    get_language_settings,
    get_active_language_choices,
    is_multilingual_project,
)

__all__ = (
    'normalize_language_code',
    'is_supported_django_language',
    'get_language_title',
    'get_language_settings',
    'get_active_language_choices',
    'is_multilingual_project',
)
