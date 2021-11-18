from django.core.cache import cache

from .testapp.models import Level2
from .utils import AppTestCase


class ModelInheritanceTests(AppTestCase):
    """
    Tests with model attributes for multiple object levels
    """

    def test_init_args(self):
        """
        Test whether passing translated attributes to __init__() works.
        """
        x = Level2(l1_title="LEVEL1", l2_title="LEVEL2", id=1)
        self.assertEqual(x.l1_title, "LEVEL1")
        self.assertEqual(x.l2_title, "LEVEL2")

    def test_save_two_levels(self):
        x = Level2(l1_title="LEVEL1", l2_title="LEVEL2", id=2)
        x.save()
        cache.clear()

        # See if fetching the object again works
        x = Level2.objects.get(pk=x.pk)
        self.assertEqual(x.l1_title, "LEVEL1")
        self.assertEqual(x.l2_title, "LEVEL2")

        # check that the translations exist after saving
        translation = Level2._parler_meta[-1].model.objects.get(master=x)
        self.assertEqual(translation.l2_title, "LEVEL2")

    def test_prefetch_levels(self):
        x = Level2(l1_title="LEVEL1", l2_title="LEVEL2", id=3)
        x.save()

        x = Level2.objects.prefetch_related("l1_translations").get(pk=x.pk)
        self.assertEqual(x.l1_title, "LEVEL1")
        self.assertEqual(x.l2_title, "LEVEL2")
