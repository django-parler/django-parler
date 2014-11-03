from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers
from .utils import create_translated_fields_serializer


class TranslatedFieldsField(serializers.WritableField):
    """
    Exposing translated fields for a TranslatableModel in REST style.
    """
    def __init__(self, *args, **kwargs):
        self.serializer_class = kwargs.pop('serializer_class', None)
        self.shared_model = kwargs.pop('shared_model', None)
        super(TranslatedFieldsField, self).__init__(*args, **kwargs)

    def initialize(self, parent, field_name):
        super(TranslatedFieldsField, self).initialize(parent, field_name)
        self._serializers = {}

        # Expect 1-on-1 for now.
        related_name = field_name

        # This could all be done in __init__(), but by moving the code here,
        # it's possible to auto-detect the parent model.
        if self.shared_model is not None and self.serializer_class is not None:
            return

        # Fill in the blanks
        if self.serializer_class is None:
            # Auto detect parent model
            if self.shared_model is None:
                self.shared_model = self.parent.opts.model

            # Create serializer based on shared model.
            translated_model = self.shared_model._parler_meta[related_name]
            self.serializer_class = create_translated_fields_serializer(self.shared_model, related_name=related_name, meta=dict(
                fields = translated_model.get_translated_fields()
            ))
        else:
            self.shared_model = self.serializer_class.Meta.model

            # Don't need to have a 'language_code', it will be split up already,
            # so this should avoid redundant output.
            if 'language_code' in self.serializer_class.base_fields:
                raise ImproperlyConfigured("Serializer may not have a 'language_code' field")

    def to_native(self, value):
        """
        Serialize to REST format.
        """
        if value is None:
            return None

        # Only need one serializer to create the native objects
        serializer = self.serializer_class()

        # Split into a dictionary per language
        ret = serializers.SortedDictWithMetadata()
        for translation in value.all():
            ret[translation.language_code] = serializer.to_native(translation)

        return ret

    def from_native(self, data, files=None):
        """
        Deserialize primitives -> objects.
        """
        self._errors = {}
        self._serializers = {}

        if data is None:
            return None
        elif isinstance(data, dict):
            # Very similar code to ModelSerializer.from_native():
            translations = self.restore_fields(data, files)
            if translations is not None:
                translations = self.perform_validation(translations)
        else:
            raise serializers.ValidationError(self.error_messages['invalid'])

        if not self._errors:
            return translations
            # No 'master' object known yet, can't store fields.
            #return self.restore_object(translations)

    def restore_fields(self, data, files):
        translations = {}
        for lang_code, model_fields in data.iteritems():
            # Create a serializer per language, so errors can be stored per serializer instance.
            self._serializers[lang_code] = serializer = self.serializer_class()
            serializer._errors = {}  # because it's .from_native() is skipped.
            translations[lang_code] = serializer.restore_fields(model_fields, files)
        return translations

    def perform_validation(self, data):
        # Runs `validate_<fieldname>()` and `validate()` methods on the serializer
        for lang_code, model_fields in data.iteritems():
            self._serializers[lang_code].perform_validation(model_fields)
        return data

#    def restore_object(self, data):
#        master = self.parent.object
#        for lang_code, model_fields in data.iteritems():
#            translation = master._get_translated_model(lang_code, auto_create=True)
#            self._serializers[lang_code].restore_object(model_fields, instance=translation)

    def validate(self, data):
        super(TranslatedFieldsField, self).validate(data)  # checks 'required' state.
        for lang_code, model_fields in data.iteritems():
            self._serializers[lang_code].validate(model_fields)
