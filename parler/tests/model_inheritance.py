from __future__ import unicode_literals
from django.core.cache import cache
from .utils import AppTestCase
from .testapp.models import Level2


class ModelInheritanceTests(AppTestCase):
    """
    Tests with model attributes for multiple object levels
    """


    def test_init_args(self):
        """
        Test whether passing translated attributes to __init__() works.
        """
        x = Level2(l1_title='LEVEL1', l2_title='LEVEL2')
        self.assertEqual(x.l1_title, "LEVEL1")
        self.assertEqual(x.l2_title, "LEVEL2")

        x.save()
        cache.clear()

        # See if fetching the object again works
        x = Level2.objects.get(pk=x.pk)
        self.assertEqual(x.l1_title, "LEVEL1")
        self.assertEqual(x.l2_title, "LEVEL2")

        # check that the translations exist after saving
        translation = Level2._parler_meta.model.objects.get(master=x)
        self.assertEqual(translation.l2_title, "LEVEL2")
