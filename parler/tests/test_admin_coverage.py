from unittest import mock

from django.contrib import admin as django_admin
from django.contrib.admin import AdminSite
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory

from parler import appsettings
from parler.admin import (
    SortedRelatedFieldListFilter,
    TranslatableAdmin,
    TranslatableStackedInline,
    TranslatableTabularInline,
)
from parler.tests.testapp.models import (
    DoubleModel,
    DoubleModelTranslations,
    RegularModel,
    SimpleModel,
)
from parler.tests.utils import AppTestCase

from article.admin import ArticleAdmin
from article.models import Article, Category


class GetQuerysetLanguageMonolingualTests(AppTestCase):
    """Lines 138, 648: monolingual path in get_queryset_language"""

    @mock.patch("parler.admin.is_multilingual_project", return_value=False)
    def test_admin_get_queryset_language_monolingual(self, _mock):
        site = AdminSite()
        ma = TranslatableAdmin(SimpleModel, site)
        req = RequestFactory().get("/")
        req.user = self.user
        lang = ma.get_queryset_language(req)
        self.assertEqual(lang, appsettings.PARLER_LANGUAGES.get_default_language())

    @mock.patch("parler.admin.is_multilingual_project", return_value=False)
    def test_inline_get_queryset_language_monolingual(self, _mock):
        class ArticleInline(TranslatableStackedInline):
            model = Article

        site = AdminSite()
        inline = ArticleInline(Category, site)
        req = RequestFactory().get("/")
        req.user = self.user
        lang = inline.get_queryset_language(req)
        self.assertEqual(lang, appsettings.PARLER_LANGUAGES.get_default_language())


class ImproperlyConfiguredTests(AppTestCase):
    """Line 152: ImproperlyConfigured for non-TranslatableQuerySet"""

    def test_get_queryset_raises_improperly_configured(self):
        site = AdminSite()
        ma = TranslatableAdmin(SimpleModel, site)
        req = RequestFactory().get("/")
        req.user = self.user
        with mock.patch(
            "django.contrib.admin.ModelAdmin.get_queryset",
            return_value=RegularModel.objects.all(),
        ):
            with self.assertRaises(ImproperlyConfigured):
                ma.get_queryset(req)


class NonTranslatableModelAdminTests(AppTestCase):
    """Lines 202, 319: non-translatable model paths"""

    def test_change_form_template_is_none_for_non_translatable(self):
        site = AdminSite()
        ma = TranslatableAdmin(RegularModel, site)
        self.assertIsNone(ma.change_form_template)

    def test_get_urls_no_delete_translation_for_non_translatable(self):
        site = AdminSite()
        ma = TranslatableAdmin(RegularModel, site)
        urls = ma.get_urls()
        names = [u.name for u in urls if hasattr(u, "name")]
        self.assertFalse(any("delete_translation" in (n or "") for n in names))


class LanguageColumnTests(AppTestCase):
    """Lines 219-220, 239: all_languages_column and untranslated span"""

    def _make_article(self, slug):
        a = Article.objects.create(published=False)
        a.set_current_language("en")
        a.title = "Test"
        a.slug = slug
        a.content = ""
        a.save()
        return a

    def test_all_languages_column(self):
        ma = django_admin.site._registry[Article]
        article = self._make_article("all-lang-test")
        result = ma.all_languages_column(article)
        self.assertIn("all-languages", result)

    def test_languages_column_shows_untranslated(self):
        ma = django_admin.site._registry[Article]
        article = self._make_article("untranslated-test")
        result = ma._languages_column(article, all_languages=["en", "nl"])
        self.assertIn("untranslated", result)


class PatchRedirectTests(AppTestCase):
    """Lines 372-373, 377, 386-403: response_change and _patch_redirect"""

    def _make_article(self, slug):
        a = Article.objects.create(published=False)
        a.set_current_language("en")
        a.title = "T"
        a.slug = slug
        a.content = ""
        a.save()
        return a

    @mock.patch("django.contrib.admin.ModelAdmin.response_change")
    def test_response_change_delegates_to_patch_redirect(self, mock_super):
        mock_super.return_value = HttpResponse("ok", status=200)
        ma = django_admin.site._registry[Article]
        req = RequestFactory().post("/")
        req.user = self.user
        article = self._make_article("rc-test")
        result = ma.response_change(req, article)
        self.assertEqual(result.status_code, 200)

    def test_patch_redirect_returns_non_redirect_as_is(self):
        ma = django_admin.site._registry[Article]
        req = RequestFactory().get("/")
        response_200 = HttpResponse("ok", status=200)
        result = ma._patch_redirect(req, Article(), response_200)
        self.assertIs(result, response_200)

    def test_patch_redirect_appends_language_to_continue_url(self):
        article = self._make_article("patch-redirect-test")
        ma = django_admin.site._registry[Article]
        req = RequestFactory().get(
            f"/en/admin/article/article/{article.pk}/change/?language=en"
        )
        req.user = self.user
        redirect = HttpResponseRedirect("../add/")
        result = ma._patch_redirect(req, article, redirect)
        self.assertIn("language=en", result["Location"])


class DeleteTranslationViewTests(AppTestCase):
    """Lines 418, 427, 455, 466, 489, 495, 514, 564: delete_translation view"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user.set_password("password")
        cls.user.save()

    def setUp(self):
        super().setUp()
        self.client.login(username="admin", password="password")

    def _make_bilingual_article(self, slug_base="del"):
        a = Article.objects.create(published=False)
        a.set_current_language("en")
        a.title = "EN"
        a.slug = f"{slug_base}-en-{a.pk}"
        a.content = ""
        a.save()
        a.set_current_language("nl")
        a.title = "NL"
        a.slug = f"{slug_base}-nl-{a.pk}"
        a.content = ""
        a.save()
        return a

    def _del_url(self, pk, lang="en"):
        return f"/en/admin/article/article/{pk}/change/delete-translation/{lang}/"

    def test_delete_translation_404_for_unknown_object(self):
        """Line 418: Http404 when shared_obj is None"""
        response = self.client.get(self._del_url(99999))
        self.assertEqual(response.status_code, 404)

    def test_delete_translation_403_no_delete_permission(self):
        """Line 427: PermissionDenied when has_delete_permission returns False"""
        article = self._make_bilingual_article("no-del-perm")
        with mock.patch.object(ArticleAdmin, "has_delete_permission", return_value=False):
            response = self.client.get(self._del_url(article.pk))
        self.assertEqual(response.status_code, 403)

    def test_delete_translation_qs_and_qs_delete_paths(self):
        """Lines 455, 564: qs.model._meta path and qs.delete() path"""
        article = self._make_bilingual_article("qs-path")
        mock_qs = mock.MagicMock()

        def fresh_gto(*args, **kwargs):
            return iter([mock_qs])

        with mock.patch("parler.admin.get_deleted_objects", return_value=([], {}, False, [])):
            with mock.patch.object(
                ArticleAdmin, "get_translation_objects", side_effect=fresh_gto
            ):
                response = self.client.post(self._del_url(article.pk), {"confirm": "yes"})
        self.assertEqual(response.status_code, 302)
        mock_qs.delete.assert_called_once()

    def test_delete_translation_403_post_perms_needed(self):
        """Line 466: PermissionDenied on POST when perms_needed"""
        article = self._make_bilingual_article("perms-needed")
        with mock.patch(
            "parler.admin.get_deleted_objects", return_value=([], {}, {"Article Translation"}, [])
        ):
            response = self.client.post(self._del_url(article.pk), {"confirm": "yes"})
        self.assertEqual(response.status_code, 403)

    def test_delete_translation_redirects_to_index_no_change_perm(self):
        """Line 489: redirect to admin:index when has_change_permission is False"""
        article = self._make_bilingual_article("no-change-perm")

        def fresh_gto(*args, **kwargs):
            return iter([mock.MagicMock()])

        with mock.patch("parler.admin.get_deleted_objects", return_value=([], {}, False, [])):
            with mock.patch.object(ArticleAdmin, "has_change_permission", return_value=False):
                with mock.patch.object(
                    ArticleAdmin, "get_translation_objects", side_effect=fresh_gto
                ):
                    response = self.client.post(self._del_url(article.pk), {"confirm": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/", response["Location"])

    def test_delete_translation_cannot_delete_title_when_perms_needed(self):
        """Line 495: 'Cannot delete' title when perms_needed=True"""
        article = self._make_bilingual_article("cannot-del")
        with mock.patch(
            "parler.admin.get_deleted_objects", return_value=([], {}, ["Article Translation"], [])
        ):
            response = self.client.get(self._del_url(article.pk))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cannot delete", response.content)

    def test_delete_translation_base_model_context(self):
        """Line 514: context updated with base_opts when admin has base_model attribute"""
        article = self._make_bilingual_article("base-model-ctx")

        class ArticleAdminWithBaseModel(ArticleAdmin):
            base_model = Article

        site = AdminSite()
        ma = ArticleAdminWithBaseModel(Article, site)
        req = RequestFactory().get("/")
        req.user = self.user

        with mock.patch("parler.admin.get_deleted_objects", return_value=([], {}, set(), [])):
            response = ma.delete_translation(req, str(article.pk), "en")
        self.assertEqual(response.status_code, 200)


class GetTranslationObjectsTests(AppTestCase):
    """Lines 579-580, 585: get_translation_objects generator paths"""

    def test_does_not_exist_continues(self):
        """Lines 579-580: DoesNotExist → continue for second translation model"""
        site = AdminSite()
        ma = TranslatableAdmin(DoubleModel, site)
        obj = DoubleModel.objects.create(shared="test")
        DoubleModelTranslations.objects.create(master=obj, language_code="en", l1_title="L1")
        # DoubleModelMoreTranslations NOT created → raises DoesNotExist → continue
        req = RequestFactory().get("/")
        req.user = self.user
        results = list(ma.get_translation_objects(req, "en", obj=obj, inlines=False))
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], list)

    def test_inlines_true_yields_qs(self):
        """Line 585: yield qs from _get_inline_translations when inlines=True"""
        ma = django_admin.site._registry[Article]
        article = Article.objects.create(published=False)
        article.set_current_language("en")
        article.title = "T"
        article.slug = "gto-inline-test"
        article.content = ""
        article.save()
        req = RequestFactory().get("/")
        req.user = self.user
        mock_qs = mock.MagicMock()

        def fake_inline_translations(request, language_code, obj=None):
            yield mock.MagicMock(), mock_qs

        with mock.patch.object(
            TranslatableAdmin, "_get_inline_translations", side_effect=fake_inline_translations
        ):
            results = list(ma.get_translation_objects(req, "en", obj=article, inlines=True))
        self.assertIn(mock_qs, results)


class GetInlineTranslationsTests(AppTestCase):
    """Lines 593-606: _get_inline_translations body coverage"""

    def test_yields_qs_for_translatable_inline_model(self):
        """Lines 593-606"""
        ma = django_admin.site._registry[Article]
        article = Article.objects.create(published=False)
        article.set_current_language("en")
        article.title = "T"
        article.slug = "git-test"
        article.content = ""
        article.save()
        req = RequestFactory().get("/")
        req.user = self.user

        mock_inline = mock.MagicMock()
        mock_inline.model = Article
        mock_formset = mock.MagicMock()
        mock_formset.fk.name = "category"
        mock_inline.get_formset.return_value = mock_formset

        category = Category.objects.create(name="test-inline-cat")
        with mock.patch.object(
            ArticleAdmin, "get_inline_instances", return_value=[mock_inline]
        ):
            results = list(ma._get_inline_translations(req, "en", obj=category))

        self.assertTrue(len(results) > 0)
        inline_obj, qs = results[0]
        self.assertIs(inline_obj, mock_inline)


class InlineAdminTests(AppTestCase):
    """Lines 680, 702, 716, 730: inline admin paths"""

    def test_get_form_language_with_translatable_parent(self):
        """Line 680: super().get_form_language() called when parent_model is translatable"""

        class ArticleInlineForSimple(TranslatableStackedInline):
            model = Article

        site = AdminSite()
        inline = ArticleInlineForSimple(SimpleModel, site)
        req = RequestFactory().get("/?language=nl")
        req.user = self.user
        lang = inline.get_form_language(req, obj=None)
        self.assertIsNotNone(lang)

    def test_get_available_languages_returns_empty_when_no_obj(self):
        """Line 702: returns empty queryset when obj is None"""

        class ArticleInlineForCategory(TranslatableStackedInline):
            model = Article

        site = AdminSite()
        inline = ArticleInlineForCategory(Category, site)
        result = inline.get_available_languages(None, mock.MagicMock())
        self.assertEqual(list(result), [])

    def test_stacked_template_when_inline_tabs_is_false(self):
        """Line 716: returns standard stacked template when inline_tabs=False"""

        class ArticleStackedForSimple(TranslatableStackedInline):
            model = Article

        site = AdminSite()
        inline = ArticleStackedForSimple(SimpleModel, site)
        self.assertFalse(inline.inline_tabs)
        self.assertEqual(inline.template, "admin/edit_inline/stacked.html")

    def test_tabular_template_when_inline_tabs_is_false(self):
        """Line 730: returns standard tabular template when inline_tabs=False"""

        class ArticleTabularForSimple(TranslatableTabularInline):
            model = Article

        site = AdminSite()
        inline = ArticleTabularForSimple(SimpleModel, site)
        self.assertFalse(inline.inline_tabs)
        self.assertEqual(inline.template, "admin/edit_inline/tabular.html")


class SortedRelatedFieldListFilterTests(AppTestCase):
    """Lines 753-754: SortedRelatedFieldListFilter.__init__"""

    def test_lookup_choices_are_sorted_alphabetically(self):
        Category.objects.create(name="Zebra")
        Category.objects.create(name="Alpha")
        req = RequestFactory().get("/")
        req.user = self.user
        field = Article._meta.get_field("category")
        ma = django_admin.site._registry[Article]
        fltr = SortedRelatedFieldListFilter(field, req, {}, Article, ma, "category")
        names = [n for _, n in fltr.lookup_choices]
        self.assertEqual(names, sorted(names, key=str.lower))
