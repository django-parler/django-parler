from __future__ import absolute_import, unicode_literals
from unittest import skipIf
import django
from django.utils import translation
from .utils import AppTestCase
from .testapp.models import SimpleModel, SimpleLightModel, SimpleRelatedModel, TranslatedSimpleRelatedModel, \
    AnotherRelatedModel


class QuerySetsTests(AppTestCase):
    def setUp(self):
        super(QuerySetsTests, self).setUp()
        self.title = 'TITLE_XX'
        self.id = SimpleModel.objects.create(tr_title=self.title).pk


@skipIf(django.VERSION < (1, 8), 'Test for django ver > 1.7')
class TranslatableQuerySetTests(QuerySetsTests):
    def setUp(self):
        super(TranslatableQuerySetTests, self).setUp()
        self.light_model_id = SimpleLightModel.objects.create(tr_title=self.title).pk

    def assertNumTranslatedQueries(self, num, qs):
        def test_qs():
            for obj in qs:
                str(obj.tr_title)
        self.assertNumQueries(num, test_qs)

    def test_select_related_light_model(self):
        with translation.override('ca-fr'):
            qs = SimpleLightModel.objects.select_related('translations').filter(pk=self.light_model_id)

            self.assertNumTranslatedQueries(1, qs.select_related('translations'))
            self.assertNumTranslatedQueries(1, qs.select_related('translations_active'))

            x = SimpleLightModel.objects.select_related('translations').get(pk=self.light_model_id)
            self.assertEqual(x.tr_title, self.title)

            x = SimpleLightModel.objects.select_related('translations_active').get(pk=self.light_model_id)
            self.assertEqual(x.tr_title, self.title)

    def test_select_related_force_model(self):
        with translation.override('ca-fr'):
            qs = SimpleModel.objects.select_related('translations').filter(pk=self.id)

            self.assertNumTranslatedQueries(1, qs.select_related('translations'))
            self.assertNumTranslatedQueries(1, qs.select_related('translations_active'))

            x = SimpleModel.objects.select_related('translations').get(pk=self.id)
            self.assertEqual(x.tr_title, self.title)

            x = SimpleModel.objects.select_related('translations_active').get(pk=self.id)
            self.assertEqual(x.tr_title, self.title)

    def test_only(self):
        with translation.override('ca-fr'):
            qs = SimpleModel.objects.all().only('id')
            self.assertNumTranslatedQueries(2, qs)  # needs query for ca-fr

            qs = SimpleModel.objects.all().only('id', 'translations_default')  # needs query for ca-fr
            self.assertNumTranslatedQueries(2, qs)

            qs = SimpleModel.objects.all().only('id', 'translations_active')  # active 'ca-fr' should been select_related
            self.assertNumTranslatedQueries(1, qs)

            qs = SimpleModel.objects.all().only('id', 'tr_title')  # should be replaced with active and default
            self.assertNumTranslatedQueries(1, qs)

            x = SimpleModel.objects.all().only('id').get(pk=self.id)
            self.assertEqual(x.tr_title, self.title)

            x = SimpleModel.objects.all().only('id', 'tr_title').get(pk=self.id)
            self.assertEqual(x.tr_title, self.title)


@skipIf(django.VERSION < (1, 8), 'Test for django ver > 1.7')
class SelectRelatedTranslationsQuerySetMixinTest(QuerySetsTests):
    def setUp(self):
        super(SelectRelatedTranslationsQuerySetMixinTest, self).setUp()
        self.related_model_id = SimpleRelatedModel.objects.create(
            some_attribute='Test', some_reference_id=self.id
        ).pk
        self.translated_related_model_id = TranslatedSimpleRelatedModel.objects.create(
            tr_attribute='Test', some_reference_id=self.id
        ).pk
        self.another_related_model_id = AnotherRelatedModel.objects.create(
            another_attribute='AnotherTest', another_reference_id=self.translated_related_model_id
        ).pk

    def test_select_related__one_degree_relation(self):
        with translation.override('ca-fr'):
            qs = SimpleRelatedModel.objects.select_related('some_reference')
            self.assertEqual(qs.query.select_related, {
                'some_reference': {'translations_active': {}, 'translations_default': {}}
            })

    def test_select_related__two_degree_relation(self):
        with translation.override('ca-fr'):
            qs = AnotherRelatedModel.objects.select_related(
                'another_reference__some_reference'
            )
            self.assertEqual(qs.query.select_related, {
                'another_reference': {'some_reference': {'translations_active': {}, 'translations_default': {}}}
            })
