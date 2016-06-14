from __future__ import unicode_literals

from django.contrib.admin import AdminSite

from parler.admin import TranslatableAdmin

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
        # See that adding a field to the admin list_display also receives the translated title
        # This happens by TranslatedFieldDescriptor.short_description
        self.assertEqual(label_for_field('tr_title', SimpleModel), "Translated Title")

    def test_list_label_abc(self):
        # See that the TranslatedFieldDescriptor of the concrete model properly routes to the proper model
        self.assertEqual(label_for_field('tr_title', ConcreteModel), "Translated Title")

        # See that the TranslatedFieldDescriptor of the abstract model handles the fallback properly.
        self.assertEqual(label_for_field('tr_title', AbstractModel), "Tr title")

    def test_default_change_form_template(self):
        site = AdminSite()
        site.register(SimpleModel, TranslatableAdmin)
        admin = site._registry[SimpleModel]
        self.assertEqual(admin.default_change_form_template, "admin/change_form.html")

        # Avoid str + __proxy__ errors
        self.assertEqual("default/" + admin.default_change_form_template, "default/admin/change_form.html")
