# following PEP 440
__version__ = "1.4"

__all__ = (
    'is_multilingual_project',
)

from .utils.i18n import is_multilingual_project
