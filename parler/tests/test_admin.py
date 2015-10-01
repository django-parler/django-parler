from __future__ import unicode_literals
try:
    from django.contrib.admin.utils import label_for_field
except ImportError:
    from django.contrib.admin.util import label_for_field
from .utils import AppTestCase
from .testapp.models import SimpleModel, ConcreteModel, AbstractModel


class AdminTests(AppTestCase):
    """
    Test admin features
    """

    def test_list_label(self):
        # Ensure model data is correct
        self.assertEqual(SimpleModel._parler_meta.root_model._meta.get_field_by_name('tr_title')[0].verbose_name, "Translated Title")

        # See that adding a field to the admin list_display also receives the translated title
        # This happens by TranslatedFieldDescriptor.short_description
        self.assertEqual(label_for_field('tr_title', SimpleModel), "Translated Title")

    def test_list_label_abc(self):
        # Ensure model data is correct
        self.assertEqual(ConcreteModel._parler_meta.root_model._meta.get_field_by_name('tr_title')[0].verbose_name, "Translated Title")

        # See that the TranslatedFieldDescriptor of the concrete model properly routes to the proper model
        self.assertEqual(label_for_field('tr_title', ConcreteModel), "Translated Title")

        # See that the TranslatedFieldDescriptor of the abstract model handles the fallback properly.
        self.assertEqual(label_for_field('tr_title', AbstractModel), "Tr title")
