"""
Tests for parler/views.py
"""
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, override_settings
from django.utils.translation import override
from django.views import generic

from parler.forms import TranslatableModelForm
from parler.views import (
    LanguageChoiceMixin,
    TranslatableModelFormMixin,
    ViewUrlMixin,
    _get_view_model,
)

from .testapp.models import SimpleModel
from .utils import AppTestCase


class ViewUrlMixinTests(AppTestCase):
    """Tests for ViewUrlMixin.get_view_url (lines 82-93)."""

    def test_get_view_url_raises_when_no_url_name(self):
        """Raises ImproperlyConfigured if view_url_name is None (lines 89-91)."""

        class MyView(ViewUrlMixin):
            pass

        view = MyView()
        with self.assertRaises(ImproperlyConfigured) as cm:
            view.get_view_url()
        self.assertIn("view_url_name", str(cm.exception))

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_get_view_url_returns_reversed_url(self):
        """Returns a reversed URL using view_url_name, args, and kwargs (line 93)."""

        class MyView(ViewUrlMixin):
            view_url_name = "article-slug-test-view"
            args = []
            kwargs = {"slug": "my-article"}

        with override("en"):
            result = MyView().get_view_url()
        self.assertIn("my-article", result)


class LanguageChoiceMixinTests(AppTestCase):
    """Tests for LanguageChoiceMixin methods (lines 213-259)."""

    def _make_view(self, obj=None):
        """Return a LanguageChoiceMixin view instance with a controllable super().get_object()."""
        the_object = obj

        class FakeBase:
            def get_object(self, queryset=None):
                return the_object

            def get_context_data(self, **kwargs):
                return dict(kwargs)

        class TestView(LanguageChoiceMixin, FakeBase):
            query_language_key = "language"
            object = None

        view = TestView()
        view.request = RequestFactory().get("/")
        view.object = None
        return view

    def test_get_object_sets_language_for_translatable(self):
        """get_object sets current language on TranslatableModel instances (lines 213-216)."""
        obj = SimpleModel.objects.language("en").create(shared="langtest", tr_title="Lang Test")
        view = self._make_view(obj=obj)
        result = view.get_object()
        self.assertEqual(result, obj)

    def test_get_language_returns_language_code(self):
        """get_language returns a language code string from request/settings (line 222)."""
        view = self._make_view()
        lang = view.get_language()
        self.assertIsNotNone(lang)
        self.assertIsInstance(lang, str)

    def test_get_default_language_returns_none(self):
        """get_default_language returns None by default (line 232)."""
        view = self._make_view()
        self.assertIsNone(view.get_default_language())

    def test_get_current_language_with_object(self):
        """get_current_language returns object's language when object is set (lines 239-240)."""
        obj = SimpleModel.objects.language("nl").create(shared="currlang", tr_title="NL")
        view = self._make_view()
        view.object = obj
        result = view.get_current_language()
        self.assertEqual(result, "nl")

    def test_get_current_language_without_object(self):
        """get_current_language falls back to get_language() when object is None (lines 241-242)."""
        view = self._make_view()
        view.object = None
        result = view.get_current_language()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_get_context_data_adds_language_tabs(self):
        """get_context_data adds language_tabs key to context (lines 245-247)."""
        view = self._make_view()
        context = view.get_context_data()
        self.assertIn("language_tabs", context)

    def test_get_language_tabs_without_object(self):
        """get_language_tabs works when object is None, yields empty available_languages (lines 253-259)."""
        view = self._make_view()
        view.object = None
        tabs = view.get_language_tabs()
        self.assertIsNotNone(tabs)

    def test_get_language_tabs_with_translatable_object(self):
        """get_language_tabs uses available_languages from the translatable object (lines 254-255)."""
        obj = SimpleModel.objects.language("en").create(shared="tabtest", tr_title="Tab Test")
        view = self._make_view()
        view.object = obj
        tabs = view.get_language_tabs()
        self.assertIsNotNone(tabs)


class TranslatableModelFormMixinTests(AppTestCase):
    """Tests for TranslatableModelFormMixin (lines 279-312)."""

    def _make_create_view(self, **overrides):
        """Return a configured TranslatableModelFormMixin+CreateView instance."""

        class TestView(TranslatableModelFormMixin, generic.CreateView):
            model = SimpleModel
            fields = ["shared"]
            success_url = "/"

        for key, val in overrides.items():
            setattr(TestView, key, val)

        view = TestView()
        view.request = RequestFactory().get("/")
        view.args = []
        view.kwargs = {}
        view.object = None
        return view

    def test_get_form_class_with_super_overridden(self):
        """If super().get_form_class is overridden in the MRO, it is called (lines 284-286)."""

        class CustomFormMixin:
            def get_form_class(self):
                return TranslatableModelForm

        class OverrideView(TranslatableModelFormMixin, CustomFormMixin, generic.CreateView):
            model = SimpleModel
            fields = ["shared"]

        view = OverrideView()
        view.request = RequestFactory().get("/")
        view.args = []
        view.kwargs = {}
        view.object = None
        result = view.get_form_class()
        self.assertIs(result, TranslatableModelForm)

    def test_get_form_class_with_form_class_set(self):
        """If form_class is set, it is returned directly (lines 289-290)."""

        class MyForm(TranslatableModelForm):
            class Meta:
                model = SimpleModel
                fields = ["shared"]

        view = self._make_create_view(form_class=MyForm, fields=None)
        result = view.get_form_class()
        self.assertIs(result, MyForm)

    def test_get_form_class_with_fields_set(self):
        """If fields is set (no form_class), modelform_factory is called with fields (lines 293-295)."""
        view = self._make_create_view(form_class=None, fields=["shared"])
        result = view.get_form_class()
        self.assertTrue(issubclass(result, TranslatableModelForm))

    def test_get_form_class_without_fields_or_form_class(self):
        """If neither form_class nor fields, modelform_factory is called without fields (lines 296-297)."""
        view = self._make_create_view(form_class=None, fields=None)
        with patch("parler.views.modelform_factory") as mock_factory:
            mock_factory.return_value = TranslatableModelForm
            result = view.get_form_class()
        mock_factory.assert_called_once_with(SimpleModel, form=TranslatableModelForm)
        self.assertIs(result, TranslatableModelForm)

    def test_get_form_kwargs_adds_current_language(self):
        """get_form_kwargs adds _current_language key to the form kwargs (lines 303-307)."""
        view = self._make_create_view()
        kwargs = view.get_form_kwargs()
        self.assertIn("_current_language", kwargs)

    def test_get_form_language_returns_current_language(self):
        """get_form_language delegates to get_current_language() (line 312)."""
        view = self._make_create_view()
        self.assertEqual(view.get_form_language(), view.get_current_language())


class GetViewModelTests(AppTestCase):
    """Tests for _get_view_model helper function (lines 337-345)."""

    def test_returns_model_when_model_is_set(self):
        """Returns self.model when it is not None (lines 337-339)."""

        class MockView:
            model = SimpleModel

        self.assertIs(_get_view_model(MockView()), SimpleModel)

    def test_returns_object_class_when_object_is_set(self):
        """Returns self.object.__class__ when model is None and object is a saved instance (lines 340-342)."""
        obj = SimpleModel.objects.language("en").create(shared="modeltest", tr_title="Model Test")

        class MockView:
            model = None

        view = MockView()
        view.object = obj
        self.assertIs(_get_view_model(view), SimpleModel)

    def test_returns_queryset_model_when_neither_set(self):
        """Returns queryset.model when both model and object are None/missing (lines 343-345)."""

        class MockView:
            model = None

            def get_queryset(self):
                return SimpleModel.objects.all()

        view = MockView()
        # No 'object' attribute at all — hasattr check returns False
        self.assertIs(_get_view_model(view), SimpleModel)
