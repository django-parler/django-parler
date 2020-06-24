from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils import translation
from parler.forms import TranslatableModelForm
from .utils import AppTestCase
from .testapp.models import (SimpleModel, UniqueTogetherModel, ForeignKeyTranslationModel, RegularModel,
                             CleanFieldModel, UUIDPrimaryKeyModel, UUIDPrimaryKeyRelatedModel,
                             IntegerPrimaryKeyModel, IntegerPrimaryKeyRelatedModel)


class SimpleForm(TranslatableModelForm):

    class Meta:
        model = SimpleModel
        fields = '__all__'


class CleanFieldForm(TranslatableModelForm):

    class Meta:
        model = CleanFieldModel
        fields = '__all__'


class UniqueTogetherForm(TranslatableModelForm):

    class Meta:
        model = UniqueTogetherModel
        fields = '__all__'


class ForeignKeyTranslationModelForm(TranslatableModelForm):

    class Meta:
        model = ForeignKeyTranslationModel
        fields = '__all__'


class IntegerPrimaryKeyForm(TranslatableModelForm):

    class Meta:
        model = IntegerPrimaryKeyModel
        fields = '__all__'


class UUIDPrimaryKeyForm(TranslatableModelForm):

    class Meta:
        model = UUIDPrimaryKeyModel
        fields = '__all__'


class OverrideMetaFieldForm(TranslatableModelForm):

    class Meta:
        model = SimpleModel
        fields = '__all__'
        help_texts = {
            'shared': 'help_text:shared',
            'tr_title': 'help_text:tr_title',
        }
        labels = {
            'shared': 'label:shared',
            'tr_title': 'label:tr_title',
        }
        error_messages = {
            'shared': { 'max_length': 'error_message:shared' },
            'tr_title': { 'max_length': 'error_message:tr_title' },
        }


class FormTests(AppTestCase):
    """
    Test model construction
    """

    def test_form_language_validation(self):
        form_instance = SimpleForm(_current_language='fr-FR')
        self.assertEqual(form_instance.language_code, 'fr-FR')

        with self.assertRaises(ValueError):
            SimpleForm(_current_language='fa')

        with self.assertRaises(ValueError):
            SimpleForm(_current_language='va_VN')

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
            x = SimpleForm(data={'shared': 'SHARED', 'tr_title': 'TRANS'})
            x.language_code = 'nl'
            self.assertFalse(x.errors)

            # Data should come out
            self.assertEqual(x.cleaned_data['shared'], 'SHARED')
            self.assertEqual(x.cleaned_data['tr_title'], 'TRANS')

            # Data should be saved
            instance = x.save()
            self.assertEqual(instance.get_current_language(), 'nl')

            x = SimpleModel.objects.language('nl').get(pk=instance.pk)
            self.assertEqual(x.shared, 'SHARED')
            self.assertEqual(x.tr_title, 'TRANS')

    def test_form_save_clean(self):
        """
        Check if the form receives and stores data.
        """
        with translation.override('fr'):
            # Initialize form in other language.
            x = CleanFieldForm(data={'shared': 'TRANS', 'tr_title': 'TEST'})
            x.language_code = 'nl'
            self.assertFalse(x.errors)

            # Data should come out
            self.assertEqual(x.cleaned_data['shared'], 'TRANS')
            self.assertEqual(x.cleaned_data['tr_title'], 'TEST')

            # Data should be saved
            instance = x.save()
            self.assertEqual(instance.get_current_language(), 'nl')

            x = CleanFieldModel.objects.language('nl').get(pk=instance.pk)
            self.assertEqual(x.shared, 'TRANS_cleanchar_cleanshared')
            self.assertEqual(x.tr_title, 'TEST_cleanchar_cleantrans')

    def test_form_save_clean_exclude(self):
        """
        Check that non-form fields are properly excluded.
        """
        class CleanPartialFieldForm(TranslatableModelForm):
            class Meta:
                model = CleanFieldModel
                fields = ('shared',)
                exclude = ('tr_title',)

        self.assertEqual(list(CleanPartialFieldForm.base_fields.keys()), ['shared'])

        with translation.override('fr'):
            x = CleanPartialFieldForm(data={'shared': 'TRANS'})
            x.language_code = 'nl'
            self.assertFalse(x.errors)

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

    def test_not_null_foreignkey_in_translation(self):
        """
        Simulate scenario for model with translation field of type foreign key (not null).
          1. User create model with one translation (EN)
          2. Switch to another language in admin (FR)
        """

        # create object with translation
        r1 = RegularModel.objects.create(original_field='r1')
        a = ForeignKeyTranslationModel.objects.create(translated_foreign=r1, shared='EN')

        # same way as TranslatableAdmin.get_object() inicializing translation, when user switch to new translation language
        a.set_current_language('fr', initialize=True)

        # inicialize form
        form = ForeignKeyTranslationModelForm(instance=a)

        self.assertTrue(True)

    def test_override_meta_fields(self):
        form_instance = OverrideMetaFieldForm(_current_language='fr-FR')
        self.assertEqual('help_text:shared', form_instance['shared'].help_text)
        self.assertEqual('help_text:tr_title', form_instance['tr_title'].help_text)
        self.assertEqual('label:shared', form_instance['shared'].label)
        self.assertEqual('label:tr_title', form_instance['tr_title'].label)

        # Override error messsages
        form_instance = OverrideMetaFieldForm(
            _current_language='fr-FR',
            data={
                'shared': 'a' * 201,
                'tr_title': 'b' * 201,
            },
        )
        self.assertEqual('error_message:shared', form_instance['shared'].errors[0])
        self.assertEqual('error_message:tr_title', form_instance['tr_title'].errors[0])


class InlineFormTests(AppTestCase):

    def test_integer_primary_key(self):
        parent_form = IntegerPrimaryKeyForm(data={'tr_title': 'TRANS'})
        self.assertTrue(parent_form.is_valid())
        parent = parent_form.save(commit=False)
        InlineFormSet = inlineformset_factory(IntegerPrimaryKeyModel, IntegerPrimaryKeyRelatedModel, fields=())
        formset = InlineFormSet(instance=parent, data={'children-TOTAL_FORMS': 1, 'children-INITIAL_FORMS': 0})
        self.assertTrue(formset.is_valid())
        parent.save()
        self.assertEqual(parent.translations.count(), 1)

    def test_uuid_primary_key(self):
        parent_form = UUIDPrimaryKeyForm(data={'tr_title': 'TRANS'})
        self.assertTrue(parent_form.is_valid())
        parent = parent_form.save(commit=False)
        self.assertIsNotNone(parent.pk)  # UUID primary key set on instantiation
        InlineFormSet = inlineformset_factory(UUIDPrimaryKeyModel, UUIDPrimaryKeyRelatedModel, fields=())
        formset = InlineFormSet(instance=parent, data={'children-TOTAL_FORMS': 1, 'children-INITIAL_FORMS': 0})
        self.assertTrue(formset.is_valid())
        self.assertIsNone(parent.pk)  # The formset above will reset the primary key
        parent.save()
        self.assertEqual(parent.translations.count(), 1)

