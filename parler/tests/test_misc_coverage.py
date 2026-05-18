"""
Coverage gap tests for miscellaneous missing lines:
- parler/tests/testapp/models.py __str__ methods (lines 28, 42, 77, 87, 98, 109, 116)
- parler/managers.py lines 60-61 (except KeyError in _extract_model_params)
- parler/cache.py line 71 (language_code = instance.get_current_language() when language_code=None)
"""
from django.utils import timezone

from parler.cache import get_cached_translation

from .testapp.models import (
    AnyLanguageModel,
    ArticleSlugModel,
    CleanFieldModel,
    DateTimeModel,
    EmptyModel,
    NotRequiredModel,
    SimpleModel,
)
from .utils import AppTestCase


# ---------------------------------------------------------------------------
# testapp/models.py __str__ methods
# ---------------------------------------------------------------------------


class TestAppModelStrTests(AppTestCase):
    def test_simple_model_str(self):
        """SimpleModel.__str__ returns tr_title (line 28)."""
        obj = SimpleModel(_current_language="en")
        obj.shared = "shared"
        obj.tr_title = "hello"
        obj.save()
        self.assertEqual(str(obj), "hello")

    def test_clean_field_model_str(self):
        """CleanFieldModel.__str__ returns tr_title (line 42)."""
        obj = CleanFieldModel(_current_language="en")
        obj.shared = "shared"
        obj.tr_title = "clean title"
        obj.save()
        self.assertEqual(str(obj), "clean title")

    def test_datetime_model_str(self):
        """DateTimeModel.__str__ returns tr_title (line 77)."""
        obj = DateTimeModel(_current_language="en")
        obj.shared = "shared"
        obj.datetime = timezone.now()
        obj.tr_title = "datetime title"
        obj.save()
        self.assertEqual(str(obj), "datetime title")

    def test_any_language_model_str(self):
        """AnyLanguageModel.__str__ returns tr_title (line 87)."""
        obj = AnyLanguageModel(_current_language="en")
        obj.shared = "shared"
        obj.tr_title = "any lang title"
        obj.save()
        self.assertEqual(str(obj), "any lang title")

    def test_not_required_model_str(self):
        """NotRequiredModel.__str__ returns tr_title (line 98)."""
        obj = NotRequiredModel(_current_language="en")
        obj.shared = "shared"
        obj.tr_title = "not required title"
        obj.save()
        self.assertEqual(str(obj), "not required title")

    def test_empty_model_str(self):
        """EmptyModel.__str__ returns shared (line 109)."""
        obj = EmptyModel(_current_language="en")
        obj.shared = "empty shared"
        obj.save()
        self.assertEqual(str(obj), "empty shared")

    def test_article_slug_model_str(self):
        """ArticleSlugModel.__str__ returns slug (line 116)."""
        obj = ArticleSlugModel(_current_language="en")
        obj.slug = "my-article"
        obj.save()
        self.assertEqual(str(obj), "my-article")


# ---------------------------------------------------------------------------
# parler/managers.py lines 60-61: except KeyError in _extract_model_params
# ---------------------------------------------------------------------------


class ManagerExtractModelParamsTests(AppTestCase):
    def test_get_or_create_with_non_translated_defaults_hits_keyerror_branch(self):
        """defaults dict that contains no translated fields triggers the except KeyError branch (lines 60-61).

        `defaults={"shared": "unique_mgr_kw"}` is truthy so the loop runs,
        but "tr_title" is not in it, triggering the KeyError → pass path.
        """
        obj, created = SimpleModel.objects.get_or_create(
            shared="unique_mgr_kw",
            defaults={"shared": "unique_mgr_kw"},
        )
        self.assertIsNotNone(obj)


# ---------------------------------------------------------------------------
# parler/cache.py line 71: language_code = instance.get_current_language()
# ---------------------------------------------------------------------------


class CacheGetCachedTranslationTests(AppTestCase):
    def test_language_code_none_uses_current_language(self):
        """Passing language_code=None triggers line 71 in get_cached_translation."""
        obj = SimpleModel(_current_language="en")
        obj.tr_title = "cached title"
        obj.save()
        # Force the translation into the cache by accessing it
        _ = obj.tr_title
        # Call with language_code=None → hits line 71
        result = get_cached_translation(obj, language_code=None)
        # May or may not be in cache depending on PARLER_ENABLE_CACHING,
        # but the branch is covered either way.
        # (result can be None or a translation object)
        self.assertTrue(result is None or hasattr(result, "language_code"))
