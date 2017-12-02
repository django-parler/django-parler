from __future__ import unicode_literals
import django
from django.test import RequestFactory
from django.utils import translation
from parler.templatetags.parler_tags import get_translated_url
from .utils import AppTestCase
from .testapp.models import ArticleSlugModel

try:
    from django.urls import reverse, resolve, get_urlconf
except ImportError:
    # Support for Django <= 1.10
    from django.core.urlresolvers import reverse, resolve, get_urlconf

try:
    from django.test.utils import override_settings  # Django 1.7+
except ImportError:
    def override_settings(ROOT_URLCONF=None):
        assert get_urlconf() == ROOT_URLCONF
        def dummy_dec(func):
            return func
        return dummy_dec


class UrlTests(AppTestCase):
    """
    Test model construction
    """
    if django.VERSION < (1, 8):
        urls = 'parler.tests.testapp.urls'

    @classmethod
    def setUpClass(cls):
        super(UrlTests, cls).setUpClass()
        article = ArticleSlugModel(_current_language=cls.conf_fallback, slug='default')
        article.set_current_language(cls.other_lang1)
        article.slug = 'lang1'
        article.set_current_language(cls.other_lang2)
        article.slug = 'lang2'
        article.save()
        cls.article = article

    def test_init_data(self):
        """
        Test whether the model is properly stored.
        """
        self.assertEqual(self.article.safe_translation_getter('slug', language_code=self.conf_fallback), 'default')
        self.assertEqual(self.article.safe_translation_getter('slug', language_code=self.other_lang1), 'lang1')
        self.assertEqual(self.article.safe_translation_getter('slug', language_code=self.other_lang2), 'lang2')

    @override_settings(ROOT_URLCONF='parler.tests.testapp.urls')
    def test_get_absolute_url(self):
        """
        Test whether the absolute URL values are correct.
        """
        self.article.set_current_language(self.conf_fallback)
        self.assertEqual(self.article.get_absolute_url(), '/{0}/article/default/'.format(self.conf_fallback))

        # Switching gives the proper URL prefix too because switch_translation(self) is applied.
        self.article.set_current_language(self.other_lang1)
        self.assertEqual(self.article.get_absolute_url(), '/{0}/article/lang1/'.format(self.other_lang1))

        self.article.set_current_language(self.other_lang2)
        self.assertEqual(self.article.get_absolute_url(), '/{0}/article/lang2/'.format(self.other_lang2))

    @override_settings(ROOT_URLCONF='parler.tests.testapp.urls')
    def test_get_translated_url(self):
        """
        Test whether get_translated_url works properly in templates.
        """
        # Pretend there is a request on /af/article-lang1/
        with translation.override(self.other_lang1):
            self.article.set_current_language(self.other_lang1)
            context = {
                'request': RequestFactory().get('/{0}/article/lang1/'.format(self.other_lang1)),
                'object': self.article
            }

            # Simulate {% get_translated_url CODE object %} syntax.
            # The object.get_absolute_url() will be used to get a translated URL.
            self.assertEqual(get_translated_url(context, lang_code=self.other_lang2), '/{0}/article/lang2/'.format(self.other_lang2))
            self.assertEqual(get_translated_url(context, lang_code=self.conf_fallback), '/{0}/article/default/'.format(self.conf_fallback))

    @override_settings(ROOT_URLCONF='parler.tests.testapp.urls')
    def test_get_translated_url_view_kwargs(self):
        """
        Test that get_translated_url can handle view kwargs.
        """
        with translation.override(self.other_lang1):
            url = reverse('view-kwargs-test-view')
            self.assertEqual(url, '/{0}/tests/kwargs-view/'.format(self.other_lang1))

            context = {
                'request': RequestFactory().get(url),
            }
            context['request'].resolver_match = resolve(url)  # Simulate WSGIHandler.get_response()

            # Simulate {% get_translated_url CODE %} syntax
            # The request.resolver_match will be used to get a translated URL.
            self.assertEqual(get_translated_url(context, lang_code=self.other_lang2), '/{0}/tests/kwargs-view/'.format(self.other_lang2))
            self.assertEqual(get_translated_url(context, lang_code=self.conf_fallback), '/{0}/tests/kwargs-view/'.format(self.conf_fallback))

    @override_settings(ROOT_URLCONF='parler.tests.testapp.urls')
    def test_get_translated_url_query_string(self):
        """
        Test that the querystring is copied to the translated URL.
        """
        # Pretend there is a request on /af/article-lang1/
        with translation.override(self.other_lang1):
            self.article.set_current_language(self.other_lang1)
            context = {
                'request': RequestFactory().get('/{0}/article/lang1/'.format(self.other_lang1), {
                    'next': '/fr/propri\xe9t\xe9/add/'
                }),
                'object': self.article
            }

            # Simulate {% get_translated_url CODE object %} syntax.
            # The object.get_absolute_url() will be used to get a translated URL.
            added_qs = "?next=%2Ffr%2Fpropri%C3%A9t%C3%A9%2Fadd%2F"
            self.assertEqual(get_translated_url(context, lang_code=self.other_lang2), '/{0}/article/lang2/{1}'.format(self.other_lang2, added_qs))
            self.assertEqual(get_translated_url(context, lang_code=self.conf_fallback), '/{0}/article/default/{1}'.format(self.conf_fallback, added_qs))

            # If the object is passed explicitly, it's likely not the current page.
            # Hence the querystring will not be copied in this case.
            self.assertEqual(get_translated_url(context, lang_code=self.other_lang2, object=self.article), '/{0}/article/lang2/'.format(self.other_lang2))

    @override_settings(ROOT_URLCONF='parler.tests.testapp.urls')
    def test_translatable_slug_mixin(self):
        """
        Test whether translated slugs are properly resolved.
        """
        # Try calls on regular translated views first
        with translation.override(self.other_lang1):  # This simulates LocaleMiddleware
            response = self.client.get('/{0}/article/lang1/'.format(self.other_lang1))
            self.assertContains(response, 'view: lang1')

        with translation.override(self.other_lang2):
            response = self.client.get('/{0}/article/lang2/'.format(self.other_lang2))
            self.assertContains(response, 'view: lang2')

    @override_settings(ROOT_URLCONF='parler.tests.testapp.urls')
    def test_translatable_slug_mixin_redirect(self):
        """
        Test whether calling a translated URL by their fallback causes a redirect.
        """
        # Try call on the default slug (which is resolvable), although there is a translated version.
        with translation.override(self.other_lang2):
            response = self.client.get('/{0}/article/default/'.format(self.other_lang2))
            if django.VERSION >= (1, 9):
                self.assertRedirects(response, '/{0}/article/lang2/'.format(self.other_lang2), status_code=301)
            elif django.VERSION >= (1, 7):
                self.assertRedirects(response, 'http://testserver/{0}/article/lang2/'.format(self.other_lang2), status_code=301)
            else:
                self.assertEqual(response.status_code, 301, "Unexpected response, got: {0}, expected 301".format(response.content))
                self.assertEqual(response['Location'], 'http://testserver/{0}/article/lang2/'.format(self.other_lang2))
