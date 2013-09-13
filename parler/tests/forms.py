from django.utils import translation
from parler.forms import TranslatableModelForm
from .utils import AppTestCase
from .testapp.models import SimpleModel


class SimpleForm(TranslatableModelForm):
    class Meta:
        model = SimpleModel


class FormTests(AppTestCase):
    """
    Test model construction
    """
    def test_form_fields(self):
        """
        Check if the form fields exist.
        """
        self.assertTrue(SimpleForm.base_fields.has_key('shared'))
        self.assertTrue(SimpleForm.base_fields.has_key('tr_title'))


    def test_form_save(self):
        """
        Check if the form receives and stores data.
        """
        with translation.override('fr'):
            # Initialize form in other language.
            x = SimpleForm(data={'shared': 'TEST', 'tr_title': 'TRANS'})
            x.language_code = 'nl'
            self.assertFalse(x.errors)

            # Data should come out
            self.assertEqual(x.cleaned_data['shared'], 'TEST')
            self.assertEqual(x.cleaned_data['tr_title'], 'TRANS')

            # Data should be saved
            instance = x.save()
            self.assertEqual(instance.get_current_language(), 'nl')

            x = SimpleModel.objects.language('nl').get(pk=instance.pk)
            self.assertEqual(x.shared, 'TEST')
            self.assertEqual(x.tr_title, 'TRANS')
