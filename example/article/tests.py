# -*- coding: utf-8 -*-
from __future__ import unicode_literals
# from django.conf import settings
from django.utils import encoding, translation
from django.test import TestCase
from django.contrib import auth
from django.core.urlresolvers import reverse
from .models import Article


class ArticleTestCase(TestCase):

    credentials = {
        'username': 'admin',
        'password': 'password'
    }

    @classmethod
    def setUpClass(cls):
        auth.models.User.objects.create_superuser(email='', **cls.credentials)

    def setUp(self):
        art = Article()
        art.set_current_language('en')
        art.title = "Cheese omelet"
        art.slug = "cheese-omelet"
        art.content = "This is the wonderful recipe of a cheese omelet."
        art.set_current_language('fr')
        art.title = "Omelette du fromage"
        art.slug = "omelette-du-fromage"
        art.content = "Voilà la recette de l'omelette au fromage"

        art.save()

        self.art_id = art.id

    def test_home(self):
        resp = self.client.get('/', follow=True)
        self.assertRedirects(resp, '/en/')
        self.assertTemplateUsed(resp, 'article/list.html')

    def test_admin_list(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_article_changelist'))
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, 'admin/change_list.html')

    def test_admin_add(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_article_add'))
        self.assertEqual(200, resp.status_code)
        self.assertIn('<h1>Add Article (English)</h1>', encoding.smart_text(resp.content))

        translation.activate('fr')
        resp = self.client.get(reverse('admin:article_article_add'))
        self.assertEqual(200, resp.status_code)
        self.assertIn('<h1>Ajout Article (Anglais)</h1>', encoding.smart_text(resp.content))

        translation.activate('en')

        resp = self.client.get(reverse('admin:article_article_add'), {"language": "nl"})
        self.assertEqual(200, resp.status_code)
        self.assertIn('<h1>Add Article (Dutch)</h1>', encoding.smart_text(resp.content))

    def test_admin_change(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_article_change', args=[self.art_id]))
        self.assertEqual(200, resp.status_code)
        self.assertIn('<h1>Change Article (English)</h1>', encoding.smart_text(resp.content))
        self.assertIn('name="title" type="text" value="Cheese omelet"', encoding.smart_text(resp.content))

        translation.activate('fr')
        resp = self.client.get(reverse('admin:article_article_change', args=[self.art_id]))
        self.assertEqual(200, resp.status_code)
        self.assertIn('<h1>Modification de Article (Anglais)</h1>', encoding.smart_text(resp.content))
        self.assertIn('name="title" type="text" value="Cheese omelet"', encoding.smart_text(resp.content))

        translation.activate('en')

        resp = self.client.get(reverse('admin:article_article_change', args=[self.art_id]), {"language": "nl"})
        self.assertEqual(200, resp.status_code)
        self.assertIn('<h1>Change Article (Dutch)</h1>', encoding.smart_text(resp.content))
        self.assertIn('name="title" type="text" />', encoding.smart_text(resp.content))
