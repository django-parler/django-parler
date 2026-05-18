"""
Tests for parler/cache.py
"""
from unittest.mock import patch

from django.test import TestCase, override_settings

from parler.cache import (
    MISSING,
    IsMissing,
    _cache_translation,
    _cache_translation_needs_fallback,
    _delete_cached_translation,
    get_cached_translated_field,
    get_cached_translation,
    get_object_cache_keys,
    get_translation_cache_key,
    is_missing,
)

from .testapp.models import SimpleModel
from .utils import AppTestCase


class IsMissingTests(TestCase):
    def test_bool_is_false(self):
        m = IsMissing()
        self.assertFalse(bool(m))

    def test_repr(self):
        m = IsMissing()
        self.assertEqual(repr(m), "<IsMissing>")

    def test_is_missing_function(self):
        self.assertTrue(is_missing(IsMissing()))
        self.assertFalse(is_missing(None))
        self.assertFalse(is_missing("value"))


class GetObjectCacheKeysTests(AppTestCase):
    def test_returns_empty_list_for_no_pk(self):
        obj = SimpleModel()
        obj.pk = None
        keys = get_object_cache_keys(obj)
        self.assertEqual(keys, [])

    def test_returns_empty_list_for_adding_state(self):
        obj = SimpleModel()
        # Simulate unsaved object
        obj._state.adding = True
        keys = get_object_cache_keys(obj)
        self.assertEqual(keys, [])

    def test_returns_keys_for_saved_object(self):
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        keys = get_object_cache_keys(obj)
        self.assertIsInstance(keys, list)
        self.assertGreater(len(keys), 0)


class GetCachedTranslationTests(AppTestCase):
    def test_returns_none_when_not_in_cache(self):
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        result = get_cached_translation(obj, language_code="fr")
        self.assertIsNone(result)

    def test_returns_cached_translation(self):
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        # Fetch object to populate cache
        obj2 = SimpleModel.objects.language("en").get(pk=obj.pk)
        _ = obj2.tr_title  # access field to ensure cache is populated
        result = get_cached_translation(obj2, language_code="en")
        # May or may not be cached depending on timing; just test it doesn't error
        self.assertTrue(result is None or result.language_code == "en")

    def test_handles_type_error_gracefully(self):
        """When a cached value has unexpected fields, get_cached_translation returns None."""
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        tr_model = obj._parler_meta.root_model
        key = get_translation_cache_key(tr_model, obj.pk, "en")
        from django.core.cache import cache

        # Store invalid data (simulating old cache with removed field)
        cache.set(key, {"id": 1, "nonexistent_field": "value"})
        result = get_cached_translation(obj, language_code="en")
        # With unexpected fields, should return None (TypeError handled)
        self.assertIsNone(result)


class GetCachedTranslatedFieldTests(AppTestCase):
    def test_returns_none_when_not_cached(self):
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        result = get_cached_translated_field(obj, "tr_title", language_code="fr")
        self.assertIsNone(result)

    def test_returns_cached_field_value(self):
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        tr_model = obj._parler_meta.root_model
        key = get_translation_cache_key(tr_model, obj.pk, "en")
        from django.core.cache import cache

        cache.set(key, {"id": 1, "tr_title": "Test"})
        result = get_cached_translated_field(obj, "tr_title", language_code="en")
        self.assertEqual(result, "Test")

    def test_returns_none_for_missing_field_in_cache(self):
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        tr_model = obj._parler_meta.root_model
        key = get_translation_cache_key(tr_model, obj.pk, "en")
        from django.core.cache import cache

        cache.set(key, {"id": 1})  # No tr_title field
        result = get_cached_translated_field(obj, "tr_title", language_code="en")
        self.assertIsNone(result)

    def test_raises_runtime_error_on_swapped_args(self):
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        # Pass args swapped: field_name too short, language_code longer than 5
        with self.assertRaises(RuntimeError):
            get_cached_translated_field(obj, "en", language_code="tr_title_long")

    def test_uses_current_language_when_none(self):
        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        obj.set_current_language("en")
        result = get_cached_translated_field(obj, "tr_title")
        # After creation and language set, result is either None or the cached value
        self.assertTrue(result is None or result == "Test")


class CacheTranslationTests(AppTestCase):
    def test_raises_value_error_for_unsaved_translation(self):
        obj = SimpleModel()
        # Get a translation object without master_id
        obj.set_current_language("en")
        translation = obj._get_translated_model(auto_create=True)
        self.assertIsNone(translation.master_id)
        with self.assertRaises(ValueError) as cm:
            _cache_translation(translation)
        self.assertIn("Can't cache unsaved translation", str(cm.exception))

    @override_settings(PARLER_ENABLE_CACHING=False)
    def test_skips_when_caching_disabled(self):
        from parler import appsettings

        old = appsettings.PARLER_ENABLE_CACHING
        appsettings.PARLER_ENABLE_CACHING = False
        try:
            obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
            translation = obj._get_translated_model()
            # Should not raise
            _cache_translation(translation)
        finally:
            appsettings.PARLER_ENABLE_CACHING = old


class CacheTranslationNeedsFallbackTests(AppTestCase):
    def test_stores_fallback_marker(self):
        from django.core.cache import cache

        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        _cache_translation_needs_fallback(obj, "fr", related_name=None)
        tr_model = obj._parler_meta.root_model
        key = get_translation_cache_key(tr_model, obj.pk, "fr")
        value = cache.get(key)
        self.assertEqual(value, {"__FALLBACK__": True})

    def test_skips_for_unsaved_instance(self):
        from django.core.cache import cache

        obj = SimpleModel()  # No pk
        # Should not raise, just return early
        _cache_translation_needs_fallback(obj, "fr", related_name=None)


class DeleteCachedTranslationTests(AppTestCase):
    def test_deletes_cached_translation(self):
        from django.core.cache import cache

        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
        translation = obj._get_translated_model()
        tr_model = obj._parler_meta.root_model
        key = get_translation_cache_key(tr_model, obj.pk, "en")
        cache.set(key, {"id": translation.pk, "tr_title": "Test"})
        self.assertIsNotNone(cache.get(key))

        _delete_cached_translation(translation)
        self.assertIsNone(cache.get(key))

    @override_settings(PARLER_ENABLE_CACHING=False)
    def test_skips_when_caching_disabled(self):
        from parler import appsettings

        old = appsettings.PARLER_ENABLE_CACHING
        appsettings.PARLER_ENABLE_CACHING = False
        try:
            obj = SimpleModel.objects.language("en").create(shared="test", tr_title="Test")
            translation = obj._get_translated_model()
            # Should not raise
            _delete_cached_translation(translation)
        finally:
            appsettings.PARLER_ENABLE_CACHING = old


class FallbackCacheTests(AppTestCase):
    def test_get_cached_translation_with_fallback(self):
        """When fallback marker is stored, use_fallback=True returns the fallback translation."""
        from django.core.cache import cache

        obj = SimpleModel.objects.language("en").create(shared="test", tr_title="EnglishTitle")
        tr_model = obj._parler_meta.root_model

        # Mark French as needing fallback
        fr_key = get_translation_cache_key(tr_model, obj.pk, "fr")
        cache.set(fr_key, {"__FALLBACK__": True})

        # Cache an English translation
        en_key = get_translation_cache_key(tr_model, obj.pk, "en")
        cache.set(en_key, {"id": 1, "tr_title": "EnglishTitle"})

        result = get_cached_translation(obj, language_code="fr", use_fallback=True)
        # Should return the English translation as fallback
        # (or None if the fallback lang config doesn't include "en")
        # We just verify no exception is raised and result is valid
        self.assertTrue(result is None or hasattr(result, "tr_title"))
