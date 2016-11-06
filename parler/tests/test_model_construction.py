
from django.db import models
from django.db.models import Manager
from django.utils import six
from parler.models import TranslatableModel
from parler.models import TranslatedFields

try:
    from unittest import expectedFailure
except ImportError:
    # python<2.7
    from django.utils.unittest import expectedFailure

from .utils import AppTestCase
from .testapp.models import ManualModel, ManualModelTranslations, SimpleModel, Level1, Level2, ProxyBase, ProxyModel, DoubleModel, RegularModel, CharModel


class ModelConstructionTests(AppTestCase):
    """
    Test model construction
    """

    def test_manual_model(self):
        """
        Test the metaclass of the model.
        """
        # Test whether the link has taken place
        self.assertIsInstance(ManualModel().translations, Manager)  # RelatedManager class
        self.assertIs(ManualModel().translations.model, ManualModelTranslations)
        self.assertIs(ManualModel._parler_meta.root_model, ManualModelTranslations)

    def test_simple_model(self):
        """
        Test the simple model syntax.
        """
        self.assertIs(SimpleModel().translations.model, SimpleModel._parler_meta.root_model)

    def test_inherited_model(self):
        """
        Test the inherited model syntax.
        """
        # First level has 1 ParlerMeta object
        self.assertEqual(Level1._parler_meta.root.rel_name, 'l1_translations')
        self.assertEqual(Level1._parler_meta.root.model.__name__, 'Level1Translation')
        self.assertEqual(len(Level1._parler_meta), 1)

        # Second level has 2 ParlerMeta objects.
        self.assertEqual(len(Level2._parler_meta), 2)
        self.assertEqual(Level2._parler_meta[0].rel_name, 'l1_translations')
        self.assertEqual(Level2._parler_meta[1].rel_name, 'l2_translations')
        self.assertEqual(Level2._parler_meta[1].model.__name__, 'Level2Translation')

        # Level 2 root attributes should point to the top-level object (Level1)
        self.assertEqual(Level2._parler_meta.root_model.__name__, 'Level1Translation')
        self.assertEqual(Level2._parler_meta.root_rel_name, 'l1_translations')
        self.assertEqual(Level2._parler_meta.root, Level1._parler_meta.root)

    def test_proxy_model(self):
        """
        Test whether proxy models can get new translations
        """
        # First level has 1 ParlerMeta object
        self.assertEqual(ProxyBase._parler_meta.root.rel_name, 'base_translations')
        self.assertEqual(len(ProxyBase._parler_meta), 1)

        # Second level has 2 ParlerMeta objects
        self.assertEqual(len(ProxyModel._parler_meta), 2)
        self.assertEqual(ProxyModel._parler_meta[0].rel_name, 'base_translations')
        self.assertEqual(ProxyModel._parler_meta[1].rel_name, 'proxy_translations')

        self.assertEqual(ProxyModel._parler_meta[0].model.__name__, 'ProxyBaseTranslation')
        self.assertEqual(ProxyModel._parler_meta[1].model.__name__, 'ProxyModelTranslation')

        # Second inheritance level attributes should point to the top-level object (ProxyBase)
        self.assertEqual(ProxyModel._parler_meta.root_model.__name__, 'ProxyBaseTranslation')
        self.assertEqual(ProxyModel._parler_meta.root_rel_name, 'base_translations')
        self.assertEqual(ProxyModel._parler_meta.root, ProxyBase._parler_meta.root)

    def test_double_translation_table(self):
        """
        Test how assigning two translation tables works.
        """
        self.assertIsNone(DoubleModel._parler_meta.base)  # Should call .add_meta() instead of overwriting/chaining it.
        self.assertEqual(len(DoubleModel._parler_meta), 2)
        self.assertEqual(DoubleModel._parler_meta[0].rel_name, "base_translations")
        self.assertEqual(DoubleModel._parler_meta[1].rel_name, "more_translations")

    def test_overlapping_proxy_model(self):
        """
        Test the simple model syntax.
        """
        from parler.tests.testapp.invalid_models import RegularModelProxy

        # Create an object without translations
        RegularModel.objects.create(id=98, original_field='untranslated')
        self.assertEqual(RegularModelProxy.objects.count(), 1)

        # Refetch from db, should raise an error.
        self.assertRaises(RuntimeError, lambda: RegularModelProxy.objects.all()[0])

    def test_model_with_different_pks(self):
        """
        Test that TranslatableModels works with different types of pks
        """
        self.assertIsInstance(SimpleModel.objects.create(tr_title='Test'), SimpleModel)
        self.assertIsInstance(CharModel.objects.create(pk='test', tr_title='Test'), CharModel)

    @expectedFailure
    def test_model_metaclass_create_order(self):
        """
        For some reason, having a custom ModelBase metaclass breaks
        the ``pk`` field detection when ``TranslatableModel`` is the first model in an inheritance chain.
        Using ``Book(Product, TranslatableModel)`` does work.
        """
        from django.db.models.base import ModelBase
        class FooModelBase(ModelBase):
            pass

        class FooModel(six.with_metaclass(FooModelBase, models.Model)):
            class Meta:
                abstract = True

        class Product(FooModel):
            pass

        class Book(TranslatableModel, Product):
            translations = TranslatedFields(
                slug=models.SlugField(blank=False, default='', max_length=128)
            )

        self.assertTrue(Book._meta.pk)
