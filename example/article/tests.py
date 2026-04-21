from collections import deque

import django
from django.contrib import auth
from django.test import TestCase
from django.test.html import Element, parse_html
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import translation
from django.utils.encoding import smart_str

from parler.appsettings import PARLER_LANGUAGES

from .models import Article, Category


class TestMixin:
    def setUp(self):
        cat = Category()
        cat.name = "Cheese"
        cat.save()
        self.cat_id = cat.id

        art = Article()
        art.set_current_language("en")
        art.title = "Cheese omelet"
        art.slug = "cheese-omelet"
        art.content = "This is the wonderful recipe of a cheese omelet."
        art.set_current_language("fr")
        art.title = "Omelette du fromage"
        art.slug = "omelette-du-fromage"
        art.content = "Voilà la recette de l'omelette au fromage"
        art.category = cat

        art.save()

        self.art_id = art.id

    def assertInContent(self, member, resp, msg=None):
        return super().assertIn(member, smart_str(resp.content), msg)

    def assertNotInContent(self, member, resp, msg=None):
        return super().assertNotIn(member, smart_str(resp.content), msg)

    def assertHTMLInContent(self, html_tag, resp):
        find_html = parse_html(html_tag)
        if find_html.children:
            raise ValueError("Can only look for single tags")
        tag_name = find_html.name
        find_attrs = dict(find_html.attributes)

        html = parse_html(smart_str(resp.content))
        queue = deque()
        queue.extend(html.children)
        while queue:
            node = queue.popleft()
            if isinstance(node, Element):
                if node.name == tag_name and _is_dict_subset(find_attrs, dict(node.attributes)):
                    return

                if node.children:
                    queue.extend(node.children)

        raise AssertionError(
            "Element <{html_tag}> not found in {html}".format(
                html_tag=html_tag,
                html=html,
            )
        )


def _is_dict_subset(d1, d2):
    # This is compatible with any version of Python, and doesn't care about dict ordering.
    return all(key in d2 and d2[key] == d1[key] for key in d1)


class ArticleTestCase(TestMixin, TestCase):
    @override_settings(ROOT_URLCONF="example.urls")
    def test_home(self):
        resp = self.client.get("/", follow=True)
        self.assertRedirects(resp, "/en/")
        self.assertTemplateUsed(resp, "article/list.html")
        self.assertNotInContent("/en/cheese-omelet", resp)

        # now published
        Article.objects.filter(id=self.art_id).update(published=True)

        resp = self.client.get(reverse("article-list"))  # == /en/
        self.assertInContent("/en/cheese-omelet", resp)

    @override_settings(ROOT_URLCONF="example.urls")
    def test_view_article(self):
        resp = self.client.get(reverse("article-details", kwargs={"slug": "cheese-omelet"}))
        self.assertEqual(404, resp.status_code)

        # now published
        Article.objects.filter(id=self.art_id).update(published=True)

        resp = self.client.get(reverse("article-details", kwargs={"slug": "cheese-omelet"}))
        self.assertTemplateUsed(resp, "article/details.html")
        self.assertInContent("This is the wonderful recipe of a cheese omelet.", resp)


class AdminArticleTestCase(TestMixin, TestCase):

    credentials = {"username": "admin", "password": "password"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user, _ = auth.models.User.objects.get_or_create(
            is_superuser=True, is_staff=True, username=cls.credentials["username"]
        )
        cls.user.set_password(cls.credentials["password"])
        cls.user.save()

    def test_admin_list(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse("admin:article_article_changelist"))
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, "admin/change_list.html")

    def test_admin_add(self):
        self.client.login(**self.credentials)

        # careful, running tests from the example app with
        # python example/manage.py test article
        # will fail, because languages declared in the settings are
        # different, and not in the same order.
        self.assertEqual("nl", PARLER_LANGUAGES.get_first_language())

        resp = self.client.get(reverse("admin:article_article_add"))
        self.assertEqual(200, resp.status_code)
        self.assertIn("<h1>Add Article (Dutch)</h1>", smart_str(resp.content))

        translation.activate("fr")
        resp = self.client.get(reverse("admin:article_article_add"))
        self.assertEqual(200, resp.status_code)

        if django.VERSION >= (5, 0):
            self.assertInContent("<h1>Ajout de Article (Néerlandais)</h1>", resp)
        elif django.VERSION >= (3, 0):
            self.assertInContent("<h1>Ajout de Article (Hollandais)</h1>", resp)
        else:
            self.assertInContent("<h1>Ajout Article (Hollandais)</h1>", resp)

        translation.activate("en")

        resp = self.client.get(reverse("admin:article_article_add"), {"language": "nl"})
        self.assertEqual(200, resp.status_code)
        self.assertInContent("<h1>Add Article (Dutch)</h1>", resp)

    def test_admin_add_post(self):
        self.client.login(**self.credentials)
        resp = self.client.post(
            reverse("admin:article_article_add"),
            {
                "title": "my article",
                "slug": "my-article",
                "content": "my super content",
            },
            follow=True,
        )

        self.assertRedirects(resp, reverse("admin:article_article_changelist"))
        self.assertEqual(1, Article.objects.filter(translations__slug="my-article").count())

    def test_admin_change(self):
        self.client.login(**self.credentials)

        # careful, running tests from the example app with
        # python example/manage.py test article
        # will fail, because languages declared in the settings are
        # different, and not in the same order.
        self.assertEqual("nl", PARLER_LANGUAGES.get_first_language())

        translation.activate("en")
        resp = self.client.get(reverse("admin:article_article_change", args=[self.art_id]))
        self.assertEqual(200, resp.status_code)
        self.assertInContent("<h1>Change Article (Dutch)</h1>", resp)

        resp = self.client.get(
            reverse("admin:article_article_change", args=[self.art_id]), {"language": "en"}
        )
        self.assertEqual(200, resp.status_code)
        self.assertInContent("<h1>Change Article (English)</h1>", resp)
        self.assertHTMLInContent('<input name="title" type="text" value="Cheese omelet">', resp)

        translation.activate("fr")
        resp = self.client.get(
            reverse("admin:article_article_change", args=[self.art_id]), {"language": "en"}
        )
        self.assertEqual(200, resp.status_code)
        self.assertInContent("<h1>Modification de Article (Anglais)</h1>", resp)
        self.assertHTMLInContent('<input name="title" type="text" value="Cheese omelet">', resp)

        translation.activate("en")

        resp = self.client.get(
            reverse("admin:article_article_change", args=[self.art_id]), {"language": "nl"}
        )
        self.assertEqual(200, resp.status_code)
        self.assertInContent("<h1>Change Article (Dutch)</h1>", resp)
        self.assertHTMLInContent('<input name="title" type="text">', resp)

    def test_admin_change_category(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse("admin:article_category_change", args=[self.cat_id]))
        self.assertEqual(200, resp.status_code)

        self.client.login(**self.credentials)
        resp = self.client.get(reverse("admin:article_stackedcategory_change", args=[self.cat_id]))
        self.assertEqual(200, resp.status_code)

        self.client.login(**self.credentials)
        resp = self.client.get(reverse("admin:article_tabularcategory_change", args=[self.cat_id]))
        self.assertEqual(200, resp.status_code)

    def test_admin_delete_translation(self):
        self.client.login(**self.credentials)
        # delete confirmation
        resp = self.client.get(
            reverse("admin:article_article_delete_translation", args=[self.art_id, "en"]),
        )
        self.assertTemplateUsed(resp, "admin/delete_confirmation.html")

        # we can go to the pagein nl even if there is no translation in that language
        translation.activate("nl")
        resp = self.client.get(
            reverse("admin:article_article_delete_translation", args=[self.art_id, "en"]),
        )
        self.assertTemplateUsed(resp, "admin/delete_confirmation.html")
        translation.activate("en")

        # delete confirmed
        resp = self.client.post(
            reverse("admin:article_article_delete_translation", args=[self.art_id, "en"]),
            {"post": "yes"},
        )
        self.assertRedirects(resp, reverse("admin:article_article_change", args=(self.art_id,)))
        self.assertEqual(0, Article.objects.filter(translations__slug="cheese-omelet").count())

        # try to delete something that is not there
        resp = self.client.post(
            reverse("admin:article_article_delete_translation", args=[self.art_id, "en"]),
            {"post": "yes"},
        )
        self.assertEqual(404, resp.status_code)

        # try to delete the only remaining translation
        translation.activate("fr")
        resp = self.client.post(
            reverse("admin:article_article_delete_translation", args=[self.art_id, "fr"]),
            {"post": "yes"},
        )
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, "admin/parler/deletion_not_allowed.html")

    def test_admin_delete_translation_unavailable(self):
        """
        To be fixed : when trying to delete the last language when a translation
        in the current language does not exist, parler fails with exception:
            Article does not have a translation for the current language!
        """
        self.client.login(**self.credentials)
        # delete confirmed
        resp = self.client.post(
            reverse("admin:article_article_delete_translation", args=[self.art_id, "en"]),
            {"post": "yes"},
        )

        # now try to delete the last translation, but the active language is english, and there is no translation in this language
        resp = self.client.post(
            reverse("admin:article_article_delete_translation", args=[self.art_id, "fr"]),
            {"post": "yes"},
        )
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, "admin/parler/deletion_not_allowed.html")

    def test_admin_delete(self):

        self.client.login(**self.credentials)
        resp = self.client.post(
            reverse("admin:article_article_changelist"),
            {
                "action": "delete_selected",
                "select_across": 0,
                "index": 0,
                "_selected_action": self.art_id,
            },
        )
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, "admin/delete_selected_confirmation.html")

        # confirmed deleteion
        resp = self.client.post(
            reverse("admin:article_article_changelist"),
            {
                "action": "delete_selected",
                "post": "yes",
                "_selected_action": self.art_id,
            },
            follow=True,
        )
        self.assertRedirects(resp, reverse("admin:article_article_changelist"))
        self.assertEqual(0, Article.objects.count())
