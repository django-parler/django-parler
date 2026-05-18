"""
Tests for parler/fields.py
"""
from unittest.mock import MagicMock

from django.core.exceptions import ImproperlyConfigured
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor

from parler.fields import (
    LanguageCodeDescriptor,
    TranslatedFieldDescriptor,
    _validate_master,
)

from .testapp.models import SimpleModel
from .utils import AppTestCase


def _make_descriptor(remote_model):
    """
    Build a ForwardManyToOneDescriptor stub pointing at remote_model.

    ForwardManyToOneDescriptor.__new__ creates the instance without calling
    __init__, then we assign .field manually so isinstance() checks pass.
    """
    descriptor = ForwardManyToOneDescriptor.__new__(ForwardManyToOneDescriptor)
    mock_field = MagicMock()
    mock_field.remote_field.model = remote_model
    descriptor.field = mock_field
    return descriptor


class ValidateMasterTests(AppTestCase):
    """Tests for _validate_master helper (lines 19-52)."""

    def test_raises_when_master_is_not_descriptor(self):
        """Raises ImproperlyConfigured when master is None, not a ForwardManyToOneDescriptor (line 24)."""

        class FakeTranslationsModel:
            master = None

        with self.assertRaises(ImproperlyConfigured) as cm:
            _validate_master(FakeTranslationsModel)
        self.assertIn("master", str(cm.exception))

    def test_raises_type_error_when_no_parler_meta(self):
        """Raises TypeError when shared model lacks _parler_meta (lines 37-38)."""

        class NoMetaModel:
            __module__ = "someapp.models"
            # No _parler_meta attribute

        class FakeTranslationsModel:
            master = _make_descriptor(NoMetaModel)

        with self.assertRaises(TypeError) as cm:
            _validate_master(FakeTranslationsModel)
        self.assertIn("TranslatableModel", str(cm.exception))

    def test_raises_when_model_already_has_translations_model(self):
        """Raises ImproperlyConfigured when _parler_meta already registers this translations class (line 44)."""
        mock_meta = MagicMock()
        mock_meta._has_translations_model.return_value = True

        class AlreadyTranslatedModel:
            __module__ = "someapp.models"
            _parler_meta = mock_meta

        class FakeTranslationsModel:
            master = _make_descriptor(AlreadyTranslatedModel)

        with self.assertRaises(ImproperlyConfigured) as cm:
            _validate_master(FakeTranslationsModel)
        self.assertIn("already has an associated translation table", str(cm.exception))

    def test_raises_when_related_name_already_used(self):
        """Raises ImproperlyConfigured when the related_name is already registered on meta (line 48)."""
        mock_meta = MagicMock()
        mock_meta._has_translations_model.return_value = False
        mock_meta._has_translations_field.return_value = True

        class DuplicateFieldModel:
            __module__ = "someapp.models"
            _parler_meta = mock_meta

        class FakeTranslationsModel:
            master = _make_descriptor(DuplicateFieldModel)

        with self.assertRaises(ImproperlyConfigured) as cm:
            _validate_master(FakeTranslationsModel)
        self.assertIn("already has an associated translation field", str(cm.exception))


class TranslatedFieldDescriptorTests(AppTestCase):
    """Tests for TranslatedFieldDescriptor (lines 120-197)."""

    def test_set_with_none_instance_raises_attribute_error(self):
        """__set__ with None instance raises AttributeError (line 159)."""
        descriptor = SimpleModel.tr_title
        with self.assertRaises(AttributeError):
            descriptor.__set__(None, "value")

    def test_delete_translated_field(self):
        """__delete__ resolves the translation and removes the attribute (lines 172-173)."""
        obj = SimpleModel.objects.language("en").create(shared="deltest", tr_title="Delete Me")
        descriptor = SimpleModel.tr_title
        # Calling __delete__ should not raise; it deletes tr_title from the translation instance
        descriptor.__delete__(obj)

    def test_repr_contains_class_and_field_names(self):
        """__repr__ returns a string identifying the class and field (line 176)."""
        descriptor = SimpleModel.tr_title
        result = repr(descriptor)
        self.assertIn("TranslatedFieldDescriptor", result)
        self.assertIn("SimpleModel", result)
        self.assertIn("tr_title", result)

    def test_short_description_returns_pretty_name_for_abstract_model(self):
        """short_description falls back to pretty_name() when translations_model is None (line 194)."""
        mock_field = MagicMock()
        mock_field.meta.model = None
        mock_field.name = "title"
        descriptor = TranslatedFieldDescriptor(mock_field)
        result = descriptor.short_description
        self.assertEqual(result, "Title")


class LanguageCodeDescriptorTests(AppTestCase):
    """Tests for LanguageCodeDescriptor (lines 200-217)."""

    def test_get_from_class_returns_descriptor_itself(self):
        """__get__ with no instance returns the descriptor object (line 207)."""
        result = SimpleModel.language_code
        self.assertIsInstance(result, LanguageCodeDescriptor)

    def test_set_raises_attribute_error_with_hint(self):
        """__set__ raises AttributeError directing users to set_current_language() (line 212)."""
        obj = SimpleModel.objects.language("en").create(shared="lc_set", tr_title="LC Set")
        with self.assertRaises(AttributeError) as cm:
            obj.language_code = "nl"
        self.assertIn("set_current_language", str(cm.exception))

    def test_delete_raises_attribute_error(self):
        """__delete__ raises AttributeError (line 217)."""
        obj = SimpleModel.objects.language("en").create(shared="lc_del", tr_title="LC Del")
        with self.assertRaises(AttributeError):
            del obj.language_code
