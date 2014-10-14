from django.db.models import Manager
from .utils import AppTestCase
from .testapp.models import ManualModel, ManualModelTranslations, SimpleModel
from parler.tests.testapp.models import ModelWithoutTranslations,\
    ExistingModelWithTranslations


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
        self.assertIs(ManualModel._translations_model, ManualModelTranslations)


    def test_simple_model(self):
        """
        Test the simple model syntax.
        """
        self.assertIs(SimpleModel().translations.model, SimpleModel._translations_model)

    def test_untranslated_model(self):
        """
        Test the simple model syntax.
        """
        self.assertTrue(ModelWithoutTranslations.objects.create().pk > 0)
        self.assertEquals(ExistingModelWithTranslations.objects.all().count(), 1)
        
        # Repeat twice because the error occurs only when saving the second time!
        # See issue #40
        for __ in range(2):
            translated_version = ExistingModelWithTranslations.objects.all()[0]
            self.assertTrue(translated_version.original_field, "untranslated")
            translated_version.original_field = "now translating"
            translated_version.save()
            self.assertEquals(ExistingModelWithTranslations.objects.all().count(), 1)
            # Refetch from db
            translated_version = ExistingModelWithTranslations.objects.all()[0]
            self.assertTrue(translated_version.original_field, "now translating")
