from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import get_urlconf, resolve, reverse
from django.utils import translation

from parler.templatetags.parler_tags import get_translated_url

from .testapp.models import ArticleSlugModel
from .utils import AppTestCase


class UrlTests(AppTestCase):
    """
    Test model construction
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        article = ArticleSlugModel(_current_language=cls.conf_fallback, slug="default")
        article.set_current_language(cls.other_lang1)
        article.slug = "lang1"
        article.set_current_language(cls.other_lang2)
        article.slug = "lang2"
        article.save()
        cls.article = article

    def test_init_data(self):
        """
        Test whether the model is properly stored.
        """
        self.assertEqual(
            self.article.safe_translation_getter("slug", language_code=self.conf_fallback),
            "default",
        )
        self.assertEqual(
            self.article.safe_translation_getter("slug", language_code=self.other_lang1), "lang1"
        )
        self.assertEqual(
            self.article.safe_translation_getter("slug", language_code=self.other_lang2), "lang2"
        )

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_get_absolute_url(self):
        """
        Test whether the absolute URL values are correct.
        """
        self.article.set_current_language(self.conf_fallback)
        self.assertEqual(
            self.article.get_absolute_url(), f"/{self.conf_fallback}/article/default/"
        )

        # Switching gives the proper URL prefix too because switch_translation(self) is applied.
        self.article.set_current_language(self.other_lang1)
        self.assertEqual(self.article.get_absolute_url(), f"/{self.other_lang1}/article/lang1/")

        self.article.set_current_language(self.other_lang2)
        self.assertEqual(self.article.get_absolute_url(), f"/{self.other_lang2}/article/lang2/")

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_get_translated_url(self):
        """
        Test whether get_translated_url works properly in templates.
        """
        # Pretend there is a request on /af/article-lang1/
        with translation.override(self.other_lang1):
            self.article.set_current_language(self.other_lang1)
            context = {
                "request": RequestFactory().get(f"/{self.other_lang1}/article/lang1/"),
                "object": self.article,
            }

            # Simulate {% get_translated_url CODE object %} syntax.
            # The object.get_absolute_url() will be used to get a translated URL.
            self.assertEqual(
                get_translated_url(context, lang_code=self.other_lang2),
                f"/{self.other_lang2}/article/lang2/",
            )
            self.assertEqual(
                get_translated_url(context, lang_code=self.conf_fallback),
                f"/{self.conf_fallback}/article/default/",
            )

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_get_translated_url_view_kwargs(self):
        """
        Test that get_translated_url can handle view kwargs.
        """
        with translation.override(self.other_lang1):
            url = reverse("view-kwargs-test-view")
            self.assertEqual(url, f"/{self.other_lang1}/tests/kwargs-view/")

            context = {
                "request": RequestFactory().get(url),
            }
            context["request"].resolver_match = resolve(url)  # Simulate WSGIHandler.get_response()

            # Simulate {% get_translated_url CODE %} syntax
            # The request.resolver_match will be used to get a translated URL.
            self.assertEqual(
                get_translated_url(context, lang_code=self.other_lang2),
                f"/{self.other_lang2}/tests/kwargs-view/",
            )
            self.assertEqual(
                get_translated_url(context, lang_code=self.conf_fallback),
                f"/{self.conf_fallback}/tests/kwargs-view/",
            )

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_get_translated_url_query_string(self):
        """
        Test that the querystring is copied to the translated URL.
        """
        # Pretend there is a request on /af/article-lang1/
        with translation.override(self.other_lang1):
            self.article.set_current_language(self.other_lang1)
            context = {
                "request": RequestFactory().get(
                    f"/{self.other_lang1}/article/lang1/", {"next": "/fr/propri\xe9t\xe9/add/"}
                ),
                "object": self.article,
            }

            # Simulate {% get_translated_url CODE object %} syntax.
            # The object.get_absolute_url() will be used to get a translated URL.
            added_qs = "?next=%2Ffr%2Fpropri%C3%A9t%C3%A9%2Fadd%2F"
            self.assertEqual(
                get_translated_url(context, lang_code=self.other_lang2),
                f"/{self.other_lang2}/article/lang2/{added_qs}",
            )
            self.assertEqual(
                get_translated_url(context, lang_code=self.conf_fallback),
                f"/{self.conf_fallback}/article/default/{added_qs}",
            )

            # If the object is passed explicitly, it's likely not the current page.
            # Hence the querystring will not be copied in this case.
            self.assertEqual(
                get_translated_url(context, lang_code=self.other_lang2, object=self.article),
                f"/{self.other_lang2}/article/lang2/",
            )

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_translatable_slug_mixin(self):
        """
        Test whether translated slugs are properly resolved.
        """
        # Try calls on regular translated views first
        with translation.override(self.other_lang1):  # This simulates LocaleMiddleware
            response = self.client.get(f"/{self.other_lang1}/article/lang1/")
            self.assertContains(response, "view: lang1")

        with translation.override(self.other_lang2):
            response = self.client.get(f"/{self.other_lang2}/article/lang2/")
            self.assertContains(response, "view: lang2")

    @override_settings(ROOT_URLCONF="parler.tests.testapp.urls")
    def test_translatable_slug_mixin_redirect(self):
        """
        Test whether calling a translated URL by their fallback causes a redirect.
        """
        # Try call on the default slug (which is resolvable), although there is a translated version.
        with translation.override(self.other_lang2):
            response = self.client.get(f"/{self.other_lang2}/article/default/")
            self.assertRedirects(response, f"/{self.other_lang2}/article/lang2/", status_code=301)
