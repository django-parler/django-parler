"""
Coverage gap tests for parler/models.py — second batch.

Covers lines that require specific cache interaction or prefetch state:
  454  - has_translation() returns True via prefetch path
  462  - has_translation() returns via memcached hit
  557  - _get_translated_model() sets MISSING marker for fallback language
  660  - _get_any_translated_model() uses prefetch[0] path
  677  - _get_translated_queryset() meta=None default
  687  - _get_prefetched_translations() meta=None default
  700  - _read_prefetched_translations() meta=None default
  707-711 - _read_prefetched_translations() loop body fills local cache
  1247 - ParlerOptions.__getitem__() raises KeyError
"""

from parler.models import MISSING, TranslationDoesNotExist

from .testapp.models import SimpleModel
from .utils import AppTestCase


class PrefetchPathTests(AppTestCase):
    """Lines 454, 707-711 — prefetch path in has_translation / _read_prefetched_translations."""

    def test_has_translation_true_via_prefetch(self):
        """has_translation returns True at line 454 when translation is in prefetch cache."""
        obj = SimpleModel.objects.language("en").create(shared="pf", tr_title="Prefetch Title")
        obj_pf = SimpleModel.objects.prefetch_related("translations").get(pk=obj.pk)
        # Clear local cache so the try-block at has_translation raises KeyError → prefetch path.
        obj_pf._translations_cache.clear()
        self.assertTrue(obj_pf.has_translation("en"))

    def test_read_prefetched_translations_loop_fills_cache(self):
        """_read_prefetched_translations loop (707-711) fills local cache from prefetch."""
        obj = SimpleModel.objects.language("en").create(shared="pf2", tr_title="Loop Title")
        obj_pf = SimpleModel.objects.prefetch_related("translations").get(pk=obj.pk)
        obj_pf._translations_cache.clear()
        meta = obj_pf._parler_meta.root
        languages = obj_pf._read_prefetched_translations(meta=meta)
        self.assertIn("en", languages)
        self.assertIn("en", obj_pf._translations_cache[meta.model])


class MemcachedHitInHasTranslationTests(AppTestCase):
    """Line 462 — memcached path in has_translation."""

    def test_has_translation_true_via_memcached(self):
        """has_translation returns True at line 462 when translation is in memcached."""
        obj = SimpleModel.objects.language("en").create(shared="mc", tr_title="Cached Title")
        # Fresh instance: empty local cache, no prefetch → hits memcached at line 462.
        obj2 = SimpleModel.objects.get(pk=obj.pk)
        self.assertTrue(obj2.has_translation("en"))

    def test_has_translation_false_via_memcached_fallback(self):
        """Line 462 returns False when memcached returns a different (fallback) language."""
        obj = SimpleModel.objects.language("en").create(shared="mc2", tr_title="En Title")

        # Trigger the FALLBACK sentinel in memcached for 'nl'.
        obj2 = SimpleModel.objects.get(pk=obj.pk)
        with self.assertRaises(TranslationDoesNotExist):
            obj2.get_translation("nl")

        # Fresh instance: memcached has __FALLBACK__ for 'nl'.
        # get_cached_translation returns the 'en' fallback object,
        # so line 462 evaluates 'en' == 'nl' → False.
        obj3 = SimpleModel.objects.get(pk=obj.pk)
        self.assertFalse(obj3.has_translation("nl"))


class FallbackMissingMarkerTests(AppTestCase):
    """Line 557 — _get_translated_model sets MISSING for the requested language when fallback used."""

    def test_fallback_missing_marker_stored_in_local_cache(self):
        """When memcached returns a fallback translation, line 557 marks original lang as MISSING."""
        obj = SimpleModel.objects.language("en").create(shared="fb", tr_title="En Title")
        meta = obj._parler_meta.root

        # Step 1: populate FALLBACK sentinel for 'nl' in memcached.
        obj2 = SimpleModel.objects.get(pk=obj.pk)
        with self.assertRaises(TranslationDoesNotExist):
            obj2.get_translation("nl")

        # Step 2: fresh instance → memcached returns 'en' fallback for 'nl' → line 557 fires.
        obj3 = SimpleModel.objects.get(pk=obj.pk)
        result = obj3._get_translated_model("nl", use_fallback=True, auto_create=False)
        self.assertEqual(result.language_code, "en")
        # After line 557, 'nl' must be marked MISSING in the local cache.
        self.assertIs(obj3._translations_cache[meta.model]["nl"], MISSING)


class GetAnyTranslatedModelPrefetchTests(AppTestCase):
    """Line 660 — _get_any_translated_model uses prefetch[0] when local cache is empty."""

    def test_get_any_uses_prefetch_list(self):
        """_get_any_translated_model returns prefetch[0] at line 660."""
        obj = SimpleModel.objects.language("en").create(shared="any", tr_title="Any Title")
        obj_pf = SimpleModel.objects.prefetch_related("translations").get(pk=obj.pk)
        # Empty local cache so the shortcut in lines 643-654 is bypassed.
        obj_pf._translations_cache.clear()
        meta = obj_pf._parler_meta.root
        translation = obj_pf._get_any_translated_model(meta=meta)
        self.assertIsNotNone(translation)
        self.assertEqual(translation.language_code, "en")


class MetaNoneDefaultTests(AppTestCase):
    """Lines 677, 687, 700 — meta=None defaults in three private helpers."""

    def setUp(self):
        super().setUp()
        self.obj = SimpleModel.objects.language("en").create(shared="mn", tr_title="Meta None")

    def test_get_translated_queryset_no_meta(self):
        """_get_translated_queryset() with no meta argument defaults to root (line 677)."""
        qs = self.obj._get_translated_queryset()
        self.assertEqual(qs.filter(language_code="en").count(), 1)

    def test_get_prefetched_translations_no_meta(self):
        """_get_prefetched_translations() with no meta argument defaults to root (line 687)."""
        # No prefetch_related was called, so result should be None.
        result = self.obj._get_prefetched_translations()
        self.assertIsNone(result)

    def test_read_prefetched_translations_no_meta(self):
        """_read_prefetched_translations() with no meta argument defaults to root (line 700)."""
        languages = self.obj._read_prefetched_translations()
        self.assertEqual(languages, [])


class ParlerOptionsGetitemKeyErrorTests(AppTestCase):
    """Line 1247 — ParlerOptions.__getitem__ raises KeyError on missing item."""

    def test_getitem_out_of_range_int_raises_key_error(self):
        """An out-of-range integer index causes IndexError → re-raised as KeyError at 1247."""
        with self.assertRaises(KeyError):
            _ = SimpleModel._parler_meta[99]

    def test_getitem_unknown_model_raises_key_error(self):
        """An unknown class triggers StopIteration → re-raised as KeyError at 1247."""

        class FakeModel:
            pass

        with self.assertRaises(KeyError):
            _ = SimpleModel._parler_meta[FakeModel]
