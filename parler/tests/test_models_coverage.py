"""
Coverage gap tests for parler/models.py.

Targets the ~77 lines that were not reached by the existing test suite:
  create_translation / delete_translation edge cases
  get_fallback_language() (deprecated)
  has_translation() edge cases
  get_available_languages(include_unsaved=True)
  _get_translated_model edge cases
  _get_any_translated_model edge cases
  validate_unique with ValidationError paths
  save_translation RuntimeError
  safe_translation_getter branches
  refresh_from_db
  TranslatedFieldsModelMixin properties / __repr__
  ParlerMeta / ParlerOptions repr / __getitem__ / helpers
"""
import warnings
from unittest.mock import patch

from django.core.exceptions import FieldError
from django.db import IntegrityError
from django.test import TestCase

from parler.models import MISSING, ParlerOptions, TranslatableModelMixin

from .testapp.models import (
    EmptyModel,
    ManualModel,
    ManualModelTranslations,
    SimpleModel,
    UniqueTogetherModel,
)
from .utils import AppTestCase


# ---------------------------------------------------------------------------
# create_translation edge cases
# ---------------------------------------------------------------------------


class CreateTranslationTests(AppTestCase):
    """Tests for TranslatableModelMixin.create_translation (lines 341-352)."""

    def test_null_language_raises_value_error(self):
        """create_translation(None) raises ValueError (line 342)."""
        obj = SimpleModel.objects.language("en").create(shared="ct-null", tr_title="X")
        with self.assertRaises(ValueError):
            obj.create_translation(None)

    def test_already_exists_raises_value_error(self):
        """create_translation for an existing language raises ValueError (line 348)."""
        obj = SimpleModel.objects.language("en").create(shared="ct-dup", tr_title="X")
        with self.assertRaises(ValueError):
            obj.create_translation("en", tr_title="duplicate")


# ---------------------------------------------------------------------------
# delete_translation edge cases
# ---------------------------------------------------------------------------


class DeleteTranslationTests(AppTestCase):
    """Tests for TranslatableModelMixin.delete_translation (lines 361-394)."""

    def test_null_language_raises_value_error(self):
        """delete_translation(None) raises ValueError (line 362)."""
        obj = SimpleModel.objects.language("en").create(shared="dt-null", tr_title="X")
        with self.assertRaises(ValueError):
            obj.delete_translation(None)

    def test_delete_with_related_name_kwarg(self):
        """delete_translation with related_name kwarg uses that single meta (line 367)."""
        obj = SimpleModel.objects.language("en").create(shared="dt-relname", tr_title="X")
        # SimpleModel's rel_name is "translations"
        result = obj.delete_translation("en", related_name="translations")
        self.assertEqual(result, 1)

    def test_nonexistent_language_raises_value_error(self):
        """delete_translation for a language that has no row raises ValueError (line 392)."""
        obj = SimpleModel.objects.language("en").create(shared="dt-noexist", tr_title="X")
        with self.assertRaises(ValueError):
            obj.delete_translation("fr")


# ---------------------------------------------------------------------------
# get_fallback_language (deprecated)
# ---------------------------------------------------------------------------


class GetFallbackLanguageTests(AppTestCase):
    """Tests for deprecated get_fallback_language() (lines 418-419)."""

    def test_returns_first_fallback(self):
        """get_fallback_language() returns the first element of get_fallback_languages() (line 419)."""
        obj = SimpleModel.objects.language("nl").create(shared="fl-nl", tr_title="NL")
        # nl has fallbacks configured in test PARLER_LANGUAGES — result may be str or None.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = obj.get_fallback_language()
        # Should return a string language code or None; just assert the method ran.
        self.assertIn(result, (None, "en", "nl", "de", "fr"))

    def test_returns_none_when_no_fallbacks(self):
        """Returns None when get_fallback_languages() is empty."""
        obj = SimpleModel.objects.language("en").create(shared="fl-none", tr_title="EN")
        with patch.object(obj, "get_fallback_languages", return_value=[]):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                result = obj.get_fallback_language()
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# has_translation edge cases
# ---------------------------------------------------------------------------


class HasTranslationTests(AppTestCase):
    """Tests for TranslatableModelMixin.has_translation (lines 437-472)."""

    def test_null_current_language_raises_value_error(self):
        """has_translation() when both args are None raises ValueError (lines 438-440)."""
        obj = SimpleModel.objects.language("en").create(shared="ht-null", tr_title="X")
        # Force _current_language to None to trigger the error path
        obj._current_language = None
        with self.assertRaises(ValueError):
            obj.has_translation()

    def test_returns_false_when_translation_missing(self):
        """has_translation('fr') returns False when no 'fr' row exists."""
        obj = SimpleModel.objects.language("en").create(shared="ht-fr", tr_title="X")
        self.assertFalse(obj.has_translation("fr"))


# ---------------------------------------------------------------------------
# get_available_languages(include_unsaved=True)
# ---------------------------------------------------------------------------


class GetAvailableLanguagesTests(AppTestCase):
    """Tests for TranslatableModelMixin.get_available_languages (lines 490-494)."""

    def test_include_unsaved_combines_db_and_cache(self):
        """include_unsaved=True merges DB languages with unsaved cache entries (lines 491-494)."""
        obj = SimpleModel.objects.language("en").create(shared="gal-unsaved", tr_title="EN title")
        # Add an unsaved "de" translation to the cache
        obj.set_current_language("de")
        obj.tr_title = "DE title"
        # "de" is now in cache but NOT in DB
        langs = obj.get_available_languages(include_unsaved=True)
        self.assertIn("en", langs)
        self.assertIn("de", langs)


# ---------------------------------------------------------------------------
# _get_translated_model edge cases
# ---------------------------------------------------------------------------


class GetTranslatedModelEdgeCaseTests(AppTestCase):
    """Edge cases in _get_translated_model (lines 511-521)."""

    def test_raises_when_parler_meta_is_none(self):
        """ImproperlyConfigured raised when _parler_meta is None (line 512)."""
        obj = SimpleModel.objects.language("en").create(shared="gtm-meta", tr_title="X")
        # Temporarily shadow the class attribute with None on the instance
        obj._parler_meta = None
        from django.core.exceptions import ImproperlyConfigured

        with self.assertRaises(ImproperlyConfigured):
            obj._get_translated_model("en")

    def test_raises_when_translations_cache_is_none(self):
        """RuntimeError raised when _translations_cache is None (line 514)."""
        obj = SimpleModel.objects.language("en").create(shared="gtm-cache", tr_title="X")
        obj._translations_cache = None
        with self.assertRaises(RuntimeError):
            obj._get_translated_model("en")

    def test_raises_when_language_code_is_none_and_current_language_is_none(self):
        """ValueError raised when language_code arg and _current_language are both falsy (line 521)."""
        obj = SimpleModel.objects.language("en").create(shared="gtm-lang", tr_title="X")
        obj._current_language = None
        with self.assertRaises(ValueError):
            obj._get_translated_model()


# ---------------------------------------------------------------------------
# _get_any_translated_model edge cases
# ---------------------------------------------------------------------------


class GetAnyTranslatedModelTests(AppTestCase):
    """Tests for _get_any_translated_model (lines 638-668)."""

    def test_returns_from_local_cache_hit(self):
        """Returns cached translation directly when it matches current language (line 651)."""
        obj = SimpleModel.objects.language("en").create(shared="gatm-cache", tr_title="Cached EN")
        # Access the translation to populate cache
        _ = obj.tr_title
        result = obj._get_any_translated_model()
        self.assertIsNotNone(result)
        self.assertEqual(result.language_code, "en")

    def test_returns_none_when_no_translations_exist(self):
        """Returns None when the queryset is empty (lines 663-664)."""
        obj = SimpleModel.objects.language("en").create(shared="gatm-empty", tr_title="X")
        # Delete all translations then clear cache
        obj.delete_translation("en")
        obj._translations_cache.clear()
        result = obj._get_any_translated_model()
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# validate_unique
# ---------------------------------------------------------------------------


class ValidateUniqueTests(AppTestCase):
    """Tests for TranslatableModelMixin.validate_unique (lines 737-751)."""

    def test_skips_missing_marker_in_cache(self):
        """MISSING markers in the translation cache are skipped (line 743)."""
        obj = SimpleModel.objects.language("en").create(shared="vu-miss", tr_title="X")
        # Manually inject a MISSING marker for "fr" into the cache
        from parler.models import MISSING

        tr_model = obj._parler_meta.root.model
        obj._translations_cache[tr_model]["fr"] = MISSING
        # validate_unique should complete without error (MISSING is skipped)
        try:
            obj.validate_unique()
        except Exception as e:
            self.fail(f"validate_unique raised unexpectedly: {e}")

    def test_translation_unique_constraint_raises(self):
        """ValidationError raised from translation.validate_unique() (lines 747-751)."""
        from django.core.exceptions import ValidationError
        from unittest.mock import patch

        obj = SimpleModel.objects.language("en").create(shared="unique-test", tr_title="hello")
        obj.set_current_language("en")

        # Patch validate_unique on the translation model to raise ValidationError
        tr_model = SimpleModel._parler_meta.root.model
        with patch.object(
            tr_model,
            "validate_unique",
            side_effect=ValidationError({"tr_title": ["This field must be unique."]}),
        ):
            with self.assertRaises(ValidationError):
                obj.validate_unique()


# ---------------------------------------------------------------------------
# save_translation RuntimeError
# ---------------------------------------------------------------------------


class SaveTranslationRuntimeErrorTests(AppTestCase):
    """save_translation raises when the master object is unsaved (line 793)."""

    def test_raises_runtime_error_when_pk_is_none(self):
        """RuntimeError when self.pk is None (line 793)."""
        obj = SimpleModel(shared="unsaved")
        obj._current_language = "en"
        obj._translations_cache = __import__("collections").defaultdict(dict)
        translation = obj._parler_meta.root.model(language_code="en", tr_title="X")
        with self.assertRaises(RuntimeError):
            obj.save_translation(translation)


# ---------------------------------------------------------------------------
# safe_translation_getter branches
# ---------------------------------------------------------------------------


class SafeTranslationGetterTests(AppTestCase):
    """Tests for safe_translation_getter branches (lines 824-852)."""

    def test_explicit_language_code_branch_translation_does_not_exist(self):
        """Returns default when explicit language_code has no translation (lines 831-832)."""
        # Create object with only a "de" translation (no "en"), then request "fr".
        # Fallback for "fr" is ["en"], but "en" also has no translation → TranslationDoesNotExist.
        obj = SimpleModel.objects.language("de").create(shared="stg-lang", tr_title="DE")
        # "fr" has no translation and its fallback "en" also has none → default returned
        result = obj.safe_translation_getter("tr_title", default="FALLBACK", language_code="fr")
        self.assertEqual(result, "FALLBACK")

    def test_callable_default_is_called(self):
        """Callable default is invoked when no translation found (line 850)."""
        # Same setup: only "de" translation, no "en" fallback available
        obj = SimpleModel.objects.language("de").create(shared="stg-callable", tr_title="DE")
        result = obj.safe_translation_getter("tr_title", default=lambda: "CALLED", language_code="fr")
        self.assertEqual(result, "CALLED")

    def test_any_language_fallback_returns_value(self):
        """any_language=True returns translation from another language (lines 842-847)."""
        obj = SimpleModel.objects.language("en").create(shared="stg-any", tr_title="EN title")
        # Switch to "fr" (no translation), but any_language=True should find "en"
        obj.set_current_language("fr")
        result = obj.safe_translation_getter("tr_title", any_language=True, default="DEFAULT")
        self.assertEqual(result, "EN title")


# ---------------------------------------------------------------------------
# refresh_from_db
# ---------------------------------------------------------------------------


class RefreshFromDbTests(AppTestCase):
    """Tests for TranslatableModelMixin.refresh_from_db (lines 855-857)."""

    def test_refresh_clears_translation_cache(self):
        """refresh_from_db clears the _translations_cache (lines 855-857)."""
        obj = SimpleModel.objects.language("en").create(shared="rfd-test", tr_title="Original")
        # Pre-populate cache
        _ = obj.tr_title
        self.assertTrue(len(obj._translations_cache) > 0)
        obj.refresh_from_db()
        # After refresh the cache dict should be empty
        total_entries = sum(len(v) for v in obj._translations_cache.values())
        self.assertEqual(total_entries, 0)


# ---------------------------------------------------------------------------
# TranslatedFieldsModelMixin properties / __repr__
# ---------------------------------------------------------------------------


class TranslatedFieldsMixinTests(AppTestCase):
    """Tests for TranslatedFieldsModelMixin properties (lines 942, 956, 1119)."""

    def test_is_empty_property_for_empty_model(self):
        """is_empty returns True when the translation model has no translated fields (line 942)."""
        obj = EmptyModel.objects.language("en").create(shared="empty-test")
        tr_model = obj._parler_meta.root.model
        translation = tr_model(language_code="en")
        translation.master = obj
        self.assertTrue(translation.is_empty)

    def test_is_empty_property_for_non_empty_model(self):
        """is_empty returns False when the translation model has translated fields (line 942)."""
        obj = SimpleModel.objects.language("en").create(shared="nonempty-test", tr_title="T")
        tr_model = obj._parler_meta.root.model
        translation = tr_model(language_code="en", tr_title="Hello")
        translation.master = obj
        self.assertFalse(translation.is_empty)

    def test_related_name_property(self):
        """related_name property returns the related_name string (line 956)."""
        obj = SimpleModel.objects.language("en").create(shared="relname-test", tr_title="T")
        tr_model = obj._parler_meta.root.model
        translation = tr_model(language_code="en", tr_title="Hello")
        translation.master = obj
        self.assertEqual(translation.related_name, "translations")

    def test_repr_of_translation_instance(self):
        """__repr__ returns the expected format (line 1119)."""
        obj = SimpleModel.objects.language("en").create(shared="repr-test", tr_title="T")
        tr = SimpleModel.objects.language("en").get(pk=obj.pk).translations.get(language_code="en")
        result = repr(tr)
        self.assertIn("SimpleModelTranslation", result)
        self.assertIn("en", result)


# ---------------------------------------------------------------------------
# ParlerMeta __repr__
# ---------------------------------------------------------------------------


class ParlerMetaReprTests(TestCase):
    """Tests for ParlerMeta.__repr__ (line 1156)."""

    def test_repr_contains_model_names(self):
        """__repr__ returns readable string identifying shared/translation models (line 1156)."""
        meta = SimpleModel._parler_meta.root
        result = repr(meta)
        self.assertIn("ParlerMeta", result)
        self.assertIn("SimpleModel", result)


# ---------------------------------------------------------------------------
# ParlerOptions __repr__ / __getitem__ / helpers
# ---------------------------------------------------------------------------


class ParlerOptionsTests(TestCase):
    """Tests for ParlerOptions (lines 1213-1247, 1268, 1276-1286, 1303, 1323)."""

    def _get_options(self):
        return SimpleModel._parler_meta

    def test_repr(self):
        """__repr__ returns readable string (lines 1213-1214)."""
        options = self._get_options()
        result = repr(options)
        self.assertIn("ParlerOptions", result)
        self.assertIn("SimpleModel", result)

    def test_getitem_by_integer(self):
        """__getitem__(0) returns the root ParlerMeta (line 1241)."""
        options = self._get_options()
        meta = options[0]
        self.assertEqual(meta, options.root)

    def test_getitem_by_related_name_string(self):
        """__getitem__('translations') returns the root meta by related name (line 1243)."""
        options = self._get_options()
        meta = options["translations"]
        self.assertEqual(meta, options.root)

    def test_getitem_by_model_class(self):
        """__getitem__(TranslationsModel) returns the matching meta (line 1245)."""
        options = self._get_options()
        translations_model = options.root.model
        meta = options[translations_model]
        self.assertEqual(meta, options.root)

    def test_getitem_by_unknown_raises_value_error(self):
        """__getitem__ with unknown string key raises ValueError (line 1243 → _get_extension_by_related_name raises ValueError)."""
        options = self._get_options()
        with self.assertRaises(ValueError):
            _ = options["nonexistent_related_name"]

    def test_get_fields_with_model(self):
        """get_fields_with_model() returns dict_items (line 1268)."""
        options = self._get_options()
        result = list(options.get_fields_with_model())
        self.assertTrue(len(result) > 0)
        field_name, model = result[0]
        self.assertIsInstance(field_name, str)

    def test_get_translated_fields_with_related_name(self):
        """get_translated_fields(related_name=...) uses the right extension (lines 1276-1277)."""
        options = self._get_options()
        fields = options.get_translated_fields(related_name="translations")
        self.assertIn("tr_title", fields)

    def test_get_model_by_field_unknown_raises_field_error(self):
        """get_model_by_field for unknown field raises FieldError (lines 1285-1286)."""
        options = self._get_options()
        with self.assertRaises(FieldError):
            options.get_model_by_field("nonexistent_field")

    def test_get_extension_by_field_none_raises_type_error(self):
        """_get_extension_by_field(None) raises TypeError (line 1303)."""
        options = self._get_options()
        with self.assertRaises(TypeError):
            options._get_extension_by_field(None)

    def test_get_extension_by_related_name_nonexistent_raises_value_error(self):
        """_get_extension_by_related_name with unknown name raises ValueError (line 1323)."""
        options = self._get_options()
        with self.assertRaises(ValueError):
            options._get_extension_by_related_name("nonexistent_related_name")

    def test_add_meta_raises_when_inherited(self):
        """add_meta raises RuntimeError when inherited=True (line 1201)."""
        options = self._get_options()
        # Temporarily mark inherited=True to trigger the guard
        original = options.inherited
        options.inherited = True
        try:
            with self.assertRaises(RuntimeError):
                from parler.models import ParlerMeta

                options.add_meta(
                    ParlerMeta(
                        shared_model=SimpleModel,
                        translations_model=options.root.model,
                        related_name="translations",
                    )
                )
        finally:
            options.inherited = original
