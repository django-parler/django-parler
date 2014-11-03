from __future__ import absolute_import
from rest_framework import serializers
from .fields import TranslatedFieldsField


class TranslatableModelSerializer(serializers.ModelSerializer):
    """
    Serializer that makes sure that translations
    from the :class:`TranslatedFieldsField` are properly saved.

    It should be used instead of the regular ``ModelSerializer``.
    """
    def save_object(self, obj, **kwargs):
        """
        Extract the translations, store these into the django-parler model data.
        """
        for meta in obj._parler_meta:
            translations = obj._related_data.pop(meta.rel_name, {})
            if translations:
                for lang_code, model_fields in translations.iteritems():
                    translations = obj._get_translated_model(lang_code, auto_create=True, meta=meta)
                    for field, value in model_fields.iteritems():
                        setattr(translations, field, value)

        return super(TranslatableModelSerializer, self).save_object(obj, **kwargs)
