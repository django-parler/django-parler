"""
Tests for parler/templatetags/parler_tags.py
"""
from django.template import Context, Template, TemplateSyntaxError
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import resolve
from django.utils.translation import activate, deactivate, override

from parler.templatetags.parler_tags import get_translated_url
from parler.utils.conf import add_default_language_settings

from .testapp.models import ArticleSlugModel, SimpleModel
from .utils import AppTestCase, override_parler_settings


class ObjectLanguageNodeTests(AppTestCase):
    """Tests for ObjectLanguageNode.__init__ and render (lines 16-18, 22-31)."""

    def test_objectlanguage_no_language_arg_uses_active_language(self):
        """objectlanguage with only the object arg uses get_language() at render time."""
        obj = SimpleModel.objects.language("en").create(shared="tag_no_lang", tr_title="Hello EN")
        t = Template(
            "{% load parler_tags %}"
            "{% objectlanguage obj %}{{ obj.tr_title }}{% endobjectlanguage %}"
        )
        activate("en")
        try:
            result = t.render(Context({"obj": obj}))
        finally:
            deactivate()
        self.assertEqual(result, "Hello EN")

    def test_objectlanguage_with_explicit_language_arg(self):
        """objectlanguage with an explicit language arg switches to that language."""
        obj = SimpleModel.objects.language("en").create(shared="tag_with_lang", tr_title="EN")
        obj.set_current_language("nl")
        obj.tr_title = "NL"
        obj.save()

        t = Template(
            "{% load parler_tags %}"
            "{% objectlanguage obj 'nl' %}{{ obj.tr_title }}{% endobjectlanguage %}"
        )
        result = t.render(Context({"obj": obj}))
        self.assertEqual(result, "NL")

    def test_objectlanguage_non_translatable_raises_syntax_error(self):
        """Rendering objectlanguage with a non-TranslatableModel raises TemplateSyntaxError."""
        t = Template(
            "{% load parler_tags %}"
            "{% objectlanguage obj %}content{% endobjectlanguage %}"
        )
        with self.assertRaises(TemplateSyntaxError):
            t.render(Context({"obj": "plain string, not a TranslatableModel"}))


class ObjectLanguageTagParsingTests(AppTestCase):
    """Tests for objectlanguage tag parsing (lines 50-64)."""

    def test_objectlanguage_too_few_args_raises(self):
        """Parsing objectlanguage with no args (only tag name) raises TemplateSyntaxError."""
        with self.assertRaises(TemplateSyntaxError):
            Template(
                "{% load parler_tags %}"
                "{% objectlanguage %}content{% endobjectlanguage %}"
            )

    def test_objectlanguage_too_many_args_raises(self):
        """Parsing objectlanguage with 4+ args raises TemplateSyntaxError."""
        with self.assertRaises(TemplateSyntaxError):
            Template(
                "{% load parler_tags %}"
                "{% objectlanguage obj 'en' extra_arg %}content{% endobjectlanguage %}"
            )


class GetTranslatedUrlTests(AppTestCase):
    """Tests for get_translated_url branches not covered by test_urls.py."""

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_view_with_get_view_url_method(self):
        """When view.get_view_url() exists, it is called and URL is returned (lines 128-129)."""

        class MockView:
            def get_view_url(self):
                return "/en/article/some-slug/"

        with override("en"):
            request = RequestFactory().get("/en/article/some-slug/")
            context = {
                "request": request,
                "view": MockView(),
            }
            result = get_translated_url(context, "en")
        self.assertEqual(result, "/en/article/some-slug/")

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_view_without_object_attr_falls_through(self):
        """View with no 'object' attribute causes getattr fallback (line 134)."""

        class MockView:
            pass  # No get_view_url, no 'object' attribute

        with override("en"):
            url = "/en/tests/kwargs-view/"
            request = RequestFactory().get(url)
            request.resolver_match = resolve(url)
            context = {
                "request": request,
                "view": MockView(),
                # No 'object' key → after lines 112-116 object is None
                # → line 133 triggers getattr(view, 'object', None) → None
                # → falls through to resolver_match handling
            }
            result = get_translated_url(context, "en")
        self.assertIn("kwargs-view", result)

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_non_translatable_object_uses_smart_override(self):
        """A non-TranslatableModel object with get_absolute_url uses smart_override (lines 150-151)."""

        class SimplePage:
            def get_absolute_url(self):
                return "/some-static-page/"

        with override("en"):
            request = RequestFactory().get("/some-static-page/")
            context = {
                "request": request,
                "object": SimplePage(),
            }
            result = get_translated_url(context, "en")
        self.assertEqual(result, "/some-static-page/")

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_translation_does_not_exist_returns_empty_string(self):
        """TranslationDoesNotExist is caught and returns '' (lines 152-155)."""
        obj = ArticleSlugModel.objects.language("en").create(slug="only-english")

        # Disable fallbacks so accessing Dutch translation raises TranslationDoesNotExist
        no_fallback_langs = add_default_language_settings(
            {
                4: ({"code": "nl"}, {"code": "de"}, {"code": "en"}),
                "default": {"fallbacks": [], "code": "en"},
            }
        )
        with override_parler_settings(PARLER_LANGUAGES=no_fallback_langs):
            with override("en"):
                request = RequestFactory().get("/en/article/only-english/")
                context = {
                    "request": request,
                    "object": obj,
                }
                # Requesting Dutch URL; object has no Dutch translation and fallback is disabled
                result = get_translated_url(context, "nl")
        self.assertEqual(result, "")

    def test_resolver_match_none_returns_empty_string(self):
        """When request.resolver_match is None (404 page), returns '' (line 163)."""
        request = RequestFactory().get("/nonexistent-page/")
        request.resolver_match = None
        context = {
            "request": request,
            # No object, no view → falls to resolver_match check
        }
        result = get_translated_url(context, "en")
        self.assertEqual(result, "")


class GetTranslatedFieldFilterTests(AppTestCase):
    """Tests for get_translated_field filter (line 193)."""

    def test_get_translated_field_filter_returns_value(self):
        """get_translated_field filter calls safe_translation_getter with the active language."""
        obj = SimpleModel.objects.language("en").create(shared="filter_test", tr_title="FilterEN")
        t = Template(
            "{% load parler_tags %}"
            "{{ obj|get_translated_field:'tr_title' }}"
        )
        activate("en")
        try:
            result = t.render(Context({"obj": obj}))
        finally:
            deactivate()
        self.assertEqual(result, "FilterEN")
