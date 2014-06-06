from django.core.urlresolvers import reverse
from django.test import RequestFactory
from django.utils import translation
from parler.templatetags.parler_tags import get_translated_url
from .utils import AppTestCase
from .testapp.models import ArticleSlugModel


class UrlTests(AppTestCase):
    """
    Test model construction
    """
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

            # Simulate {% get_translated_url CODE object %} syntax
            self.assertEqual(get_translated_url(context, lang_code=self.other_lang2), '/{0}/article/lang2/'.format(self.other_lang2))
            self.assertEqual(get_translated_url(context, lang_code=self.conf_fallback), '/{0}/article/default/'.format(self.conf_fallback))

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

            # Simulate {% get_translated_url CODE object %} syntax
            self.assertEqual(get_translated_url(context, lang_code=self.other_lang2), '/{0}/tests/kwargs-view/'.format(self.other_lang2))
            self.assertEqual(get_translated_url(context, lang_code=self.conf_fallback), '/{0}/tests/kwargs-view/'.format(self.conf_fallback))

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

    def test_translatable_slug_mixin_redirect(self):
        """
        Test whether calling a translated URL by their fallback causes a redirect.
        """
        # Try call on the default slug (which is resolvable), although there is a translated version.
        with translation.override(self.other_lang2):
            response = self.client.get('/{0}/article/default/'.format(self.other_lang2))
            self.assertEqual(response.status_code, 301, "Unexpected response, got: {0}, expected 301".format(response.content))
            self.assertEqual(response['Location'], 'http://testserver/{0}/article/lang2/'.format(self.other_lang2))
