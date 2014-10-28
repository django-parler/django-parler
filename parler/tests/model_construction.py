from django.db.models import Manager
from .utils import AppTestCase
from .testapp.models import ManualModel, ManualModelTranslations, SimpleModel, Level1, Level2


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
        self.assertEqual(Level1._parler_meta.rel_name, 'l1_translations')
        self.assertEqual(Level2._parler_meta.rel_name, 'l2_translations')

        self.assertEqual(Level1._parler_meta.model.__name__, 'Level1Translation')
        self.assertEqual(Level2._parler_meta.model.__name__, 'Level2Translation')

        # Level 2 root attributes should point to the top-level object (Level1)
        self.assertEqual(Level2._parler_meta.root_model.__name__, 'Level1Translation')
        self.assertEqual(Level2._parler_meta.root_rel_name, 'l1_translations')
        self.assertEqual(Level2._parler_meta.root, Level1._parler_meta)
