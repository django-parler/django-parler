"""
This package provides support for integrating translatable fields into *django-rest-framework*.
"""
from .fields import TranslatedFieldsField
from .serializers import TranslatableModelSerializer

__all__ = (
    'TranslatedFieldsField',
    'TranslatableModelSerializer',
)
