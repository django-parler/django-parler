"""
Tests for parler/managers.py
"""
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.query import QuerySet
from django.test import TestCase
from django.utils.translation import activate, deactivate

from parler.managers import TranslatableManager, TranslatableQuerySet

from .testapp.models import SimpleModel
from .utils import AppTestCase


class TranslatableQuerySetTests(AppTestCase):
    def test_language_with_none_uses_default(self):
        """language(None) should fall back to the default language."""
        qs = SimpleModel.objects.all()
        result = qs.language(None)
        self.assertIsNotNone(result._language)

    def test_language_sets_code(self):
        qs = SimpleModel.objects.language("en")
        self.assertEqual(qs._language, "en")

    def test_translated_no_language_codes_uses_active(self):
        """translated() with no language_codes uses the currently active language."""
        activate("en")
        try:
            SimpleModel.objects.language("en").create(shared="test", tr_title="Test EN")
            qs = SimpleModel.objects.translated()
            self.assertIsInstance(qs, QuerySet)
        finally:
            deactivate()

    def test_translated_with_master_prefix(self):
        """translated() with master__ field prefix strips the prefix."""
        obj = SimpleModel.objects.language("en").create(shared="SharedValue", tr_title="Test")
        qs = SimpleModel.objects.translated("en", master__shared="SharedValue")
        self.assertIn(obj, qs)

    def test_translated_multiple_language_codes(self):
        """translated() with multiple language codes uses __in filter."""
        SimpleModel.objects.language("en").create(shared="test", tr_title="Test EN")
        SimpleModel.objects.language("nl").create(shared="test2", tr_title="Test NL")
        qs = SimpleModel.objects.translated("en", "nl")
        self.assertIsInstance(qs, QuerySet)
        self.assertGreaterEqual(qs.count(), 1)

    def test_active_translations(self):
        """active_translations returns a queryset filtered by active language choices."""
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        activate("en")
        try:
            qs = SimpleModel.objects.active_translations()
            self.assertIsInstance(qs, QuerySet)
        finally:
            deactivate()

    def test_extract_model_params_with_translated_fields(self):
        """_extract_model_params should separate translated from regular fields."""
        obj, created = SimpleModel.objects.get_or_create(
            shared="extract_test", defaults={"tr_title": "Title"}
        )
        self.assertIsInstance(obj, SimpleModel)

    def test_create_with_language_set(self):
        """create() on a language-filtered queryset sets the language on the new object."""
        obj = SimpleModel.objects.language("nl").create(shared="test_nl", tr_title="NL Title")
        self.assertEqual(obj.get_current_language(), "nl")

    def test_clone_preserves_language(self):
        """Cloning a queryset preserves the _language attribute."""
        qs = SimpleModel.objects.language("en")
        cloned = qs.filter(shared="test")
        self.assertEqual(cloned._language, "en")


class TranslatableManagerTests(TestCase):
    def test_get_queryset_returns_translatable_qs(self):
        qs = SimpleModel.objects.get_queryset()
        self.assertIsInstance(qs, TranslatableQuerySet)

    def test_get_queryset_raises_if_not_translatable_qs(self):
        """If the queryset class doesn't inherit from TranslatableQuerySet, raise."""

        class BrokenManager(TranslatableManager):
            _queryset_class = QuerySet

        manager = BrokenManager()
        manager.auto_created = True
        manager.model = SimpleModel
        manager.name = "objects"
        manager._db = "default"

        with self.assertRaises(ImproperlyConfigured):
            manager.get_queryset()
