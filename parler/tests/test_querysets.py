from __future__ import absolute_import, unicode_literals
from unittest import skipIf
import django

from parler import appsettings
from django.utils import translation
from .utils import AppTestCase
from .testapp.models import SimpleModel, SimpleLightModel, SimpleModelA, SimpleModelB, SimpleModelC, \
    SimpleNonTranslatableModelC


@skipIf(django.VERSION < (1, 8), 'Test for django ver > 1.7')
class QuerySetsTests(AppTestCase):
    def setUp(self):
        super(QuerySetsTests, self).setUp()
        self.title = 'TITLE_XX'
        self.shared = 'SHARED'
        self.id = SimpleModel.objects.create(tr_title=self.title, shared=self.shared).pk
        self.light_model_id = SimpleLightModel.objects.create(tr_title=self.title, shared=self.shared).pk
        self.PARLER_ENABLE_CACHING = appsettings.PARLER_ENABLE_CACHING
        appsettings.PARLER_ENABLE_CACHING = False
        self.qs = SimpleModel.objects.all()
        self.light_qs = SimpleLightModel.objects.all()

    def tearDown(self):
        appsettings.PARLER_ENABLE_CACHING = self.PARLER_ENABLE_CACHING
        super(QuerySetsTests, self).tearDown()

    def assertNumTranslatedQueries(self, num, qs):
        def test_qs():
            for obj in qs:
                title = str(obj.tr_title)
                self.assertEqual(title, self.title)
        self.assertNumQueries(num, test_qs)

    def test_auto_adds_select_related(self):
        self.assertNumTranslatedQueries(1, self.qs)

    def test_auto_adds_select_related_fallback(self):
        with translation.override('ca-fr'):
            self.assertNumTranslatedQueries(1, self.qs)

    def test_not_auto_adds_select_related_with_no_force(self):
        # needs additional query for en
        self.assertNumTranslatedQueries(2, self.light_qs.all())
        with translation.override('ca-fr'):
            # needs 2 additional queries for ca-fr and en (fallback)
            self.assertNumTranslatedQueries(3, self.light_qs.all())

    def test_select_related_light_model(self):
        with translation.override('ca-fr'):
            self.assertNumTranslatedQueries(1, self.light_qs.select_related('translations'))
            self.assertNumTranslatedQueries(1, self.light_qs.select_related('translations_active'))

    def test_select_related_force_model(self):
        with translation.override('ca-fr'):
            self.assertNumTranslatedQueries(1, self.qs.select_related('translations'))
            self.assertNumTranslatedQueries(1, self.qs.select_related('translations_active'))

    def test_only(self):
        with translation.override('ca-fr'):
            # needs 2 additional queries for ca-fr and en
            self.assertNumTranslatedQueries(3, self.qs.only('id'))

            # needs query for ca-fr (active)
            self.assertNumTranslatedQueries(2, self.qs.only('id', 'translations_default'))

            # needs query for en (default)
            self.assertNumTranslatedQueries(2, self.qs.only('id', 'translations_active'))

            self.assertNumTranslatedQueries(1, self.qs.only('id', 'translations_active', 'translations_default'))

            # no needs additional, should be replaced with active and default
            self.assertNumTranslatedQueries(1, self.qs.only('id', 'tr_title'))

            # no needs additional, should be replaced with active and default
            self.assertNumTranslatedQueries(1, self.qs.only('id', 'translations'))

    def test_not_auto_adds_select_related_when_update(self):
        qs = self.qs.select_for_update().filter(pk=self.id)
        self.assertNumTranslatedQueries(2, qs)

    def test_auto_adds_select_related_with_iterators(self):
        self.assertNumTranslatedQueries(1, self.qs.iterator())

    def test_defer__related_not_auto_adds(self):
        with translation.override('ca-fr'):
            self.assertNumTranslatedQueries(3, self.qs.defer('translations_default', 'translations_active'))
            self.assertNumTranslatedQueries(2, self.qs.defer('translations_active'))
            self.assertNumTranslatedQueries(2, self.qs.defer('translations_default'))

    def test_values_list(self):
        with translation.override('ca-fr'):
            values_list = self.qs.values_list('id', 'shared')
            self.assertListEqual(list(values_list), [(self.id, self.shared)])
            values_list = self.qs.values_list('shared', flat=True)
            self.assertListEqual(list(values_list), [self.shared])

    def test_values_list_with_translations(self):
        with translation.override('ca-fr'):
            values_list = self.qs.values_list('id', 'translations__tr_title', 'shared')
            self.assertListEqual(list(values_list), [(self.id, self.title, self.shared)])
            values_list = self.qs.values_list('id', 'translations_default__tr_title', 'shared')
            self.assertListEqual(list(values_list), [(self.id, self.title, self.shared)])
            values_list = self.qs.values_list('id', 'translations_active__tr_title', 'shared')
            self.assertListEqual(list(values_list), [(self.id, None, self.shared)])

    def test_values(self):
        with translation.override('ca-fr'):
            values = self.qs.values('id', 'shared')
            self.assertEqual(len(values), 1)
            self.assertDictEqual(values[0], {
                'id': self.id,
                'shared': self.shared,
            })

    def test_values_with_translations(self):
        with translation.override('ca-fr'):
            values = self.qs.values('id', 'translations__tr_title', 'shared')
            self.assertEqual(len(values), 1)
            self.assertDictEqual(values[0], {
                'id': self.id,
                'translations__tr_title': self.title,
                'shared': self.shared,
            })
            values = self.qs.values('id', 'translations_default__tr_title', 'shared')
            self.assertEqual(len(values), 1)
            self.assertDictEqual(values[0], {
                'id': self.id,
                'translations_default__tr_title': self.title,
                'shared': self.shared,
            })
            values = self.qs.values('id', 'translations_active__tr_title', 'shared')
            self.assertEqual(len(values), 1)
            self.assertDictEqual(values[0], {
                'id': self.id,
                'translations_active__tr_title': None,
                'shared': self.shared,
            })


@skipIf(django.VERSION < (1, 8), 'Test for django ver > 1.7')
class SelectRelatedTranslationsQuerySetMixinTests(AppTestCase):
    def setUp(self):
        super(SelectRelatedTranslationsQuerySetMixinTests, self).setUp()
        self.model_a = SimpleModelA.objects.create(model_a_title='TITLE_A')
        self.model_b = SimpleModelB.objects.create(model_b_title='TITLE_B', model_a=self.model_a)
        self.model_c = SimpleModelC.objects.create(model_c_title='TITLE_C', model_b=self.model_b)
        self.model_c_non_translatable = SimpleNonTranslatableModelC.objects.create(
            model_c_title='TITLE_C',
            model_b=self.model_b,
        )
        self.PARLER_ENABLE_CACHING = appsettings.PARLER_ENABLE_CACHING
        appsettings.PARLER_ENABLE_CACHING = False
        self.qs = SimpleModelC.objects.all()
        self.qs_non_translatable = SimpleNonTranslatableModelC.objects.all()

    def tearDown(self):
        appsettings.PARLER_ENABLE_CACHING = self.PARLER_ENABLE_CACHING
        super(SelectRelatedTranslationsQuerySetMixinTests, self).tearDown()

    def assertTitle(self, obj):
        self.assertEqual(obj.tr_title, self.title)

    def assertNumTranslatedQueries(self, num, qs):
        def test_qs():
            for obj in qs:
                title_c = obj.model_c_title
                title_b = obj.model_b.model_b_title
                title_a = obj.model_b.model_a.model_a_title
                self.assertEqual(title_c, 'TITLE_C')
                self.assertEqual(title_b, 'TITLE_B')
                self.assertEqual(title_a, 'TITLE_A')
        self.assertNumQueries(num, test_qs)

    def test_without_select_related(self):
        with translation.override('ca-fr'):
            # should be 2 additionaly query from testapp_simplemodela and testapp_simplemodelb,
            # and 4 from testapp_simplemodela_translation and testapp_simplemodelb_translation in en and ca-fr languages
            self.assertNumTranslatedQueries(7, self.qs)
            self.assertNumTranslatedQueries(7, self.qs_non_translatable)

    def test_select_related_in_one_levels(self):
        with translation.override('ca-fr'):
            # should be 1 additionaly query from testapp_simplemodela and
            # and 2 from testapp_simplemodela_translation in en and ca-fr languages
            self.assertNumTranslatedQueries(4, self.qs.select_related('model_b'))
            self.assertNumTranslatedQueries(4, self.qs_non_translatable.select_related('model_b'))

    def test_select_related_in_two_levels(self):
        with translation.override('ca-fr'):
            self.assertNumTranslatedQueries(1, self.qs.select_related('model_b__model_a'))
            self.assertNumTranslatedQueries(1, self.qs_non_translatable.select_related('model_b__model_a'))
