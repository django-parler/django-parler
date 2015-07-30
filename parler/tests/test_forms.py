import django
from django.core.exceptions import ValidationError
from django.utils import translation
from parler.forms import TranslatableModelForm
from .utils import AppTestCase
from .testapp.models import SimpleModel, UniqueTogetherModel


class SimpleForm(TranslatableModelForm):
    class Meta:
        model = SimpleModel
        if django.VERSION >= (1,6):
            fields = '__all__'


class UniqueTogetherForm(TranslatableModelForm):
    class Meta:
        model = UniqueTogetherModel
        if django.VERSION >= (1,6):
            fields = '__all__'


class FormTests(AppTestCase):
    """
    Test model construction
    """
    def test_form_fields(self):
        """
        Check if the form fields exist.
        """
        self.assertTrue('shared' in SimpleForm.base_fields)
        self.assertTrue('tr_title' in SimpleForm.base_fields)


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


    def test_unique_together(self):
        UniqueTogetherModel(_current_language='en', slug='foo').save()

        # Different language code, no problem
        form = UniqueTogetherForm(data={'slug': 'foo'})
        form.language_code = 'fr'
        self.assertTrue(form.is_valid())

        # Same language code, should raise unique_together check
        form = UniqueTogetherForm(data={'slug': 'foo'})
        form.language_code = 'en'
        self.assertFalse(form.is_valid())
        self.assertRaises(ValidationError, lambda: form.instance.validate_unique())
