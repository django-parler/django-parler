from __future__ import unicode_literals
from django.utils import translation
from parler.models import TranslationDoesNotExist
from .utils import AppTestCase
from .testapp.models import SimpleModel, AnyLanguageModel, EmptyModel


class ModelAttributeTests(AppTestCase):
    """
    Test model construction
    """
    def test_untranslated_get(self):
        """
        Test the metaclass of the model.
        """
        try:
            value = SimpleModel().tr_title
        except Exception as e:
            self.assertIsInstance(e, TranslationDoesNotExist)
            self.assertIsInstance(e, AttributeError)
        else:
            self.fail("Expected exception from reading untranslated title, got {0}.".format(repr(value)))

        # Raising attribute error gives some additional benefits:
        self.assertEqual(getattr(SimpleModel(), 'tr_title', 'FOO'), 'FOO')
        self.assertFalse(hasattr(SimpleModel(), 'tr_title'))


    def test_default_language(self):
        """
        Test whether simple language assignments work.
        """
        with translation.override('ca-fr'):
            x = SimpleModel(id=99)   # uses get_language(), ID is to avoid reading cached items for 'en'
            self.assertEqual(x.get_current_language(), translation.get_language())
            self.assertEqual(translation.get_language(), 'ca-fr')

        x.shared = 'SHARED'
        x.tr_title = 'TRANS_CA'
        x.save()

        # Refetch
        with translation.override('en'):
            x = SimpleModel.objects.get(pk=x.pk)
            self.assertRaises(TranslationDoesNotExist, lambda: x.tr_title)

            # Switch context
            x.set_current_language('ca-fr')
            self.assertEqual(x.tr_title, 'TRANS_CA')


    def test_init_args(self):
        """
        Test whether passing translated attributes to __init__() works.
        """
        x = SimpleModel(tr_title='TRANS_TITLE')
        self.assertEqual(x.tr_title, "TRANS_TITLE")

        y = SimpleModel(tr_title='TRANS_TITLE', _current_language='nl')
        self.assertEqual(y.get_current_language(), 'nl')
        self.assertEqual(y.tr_title, "TRANS_TITLE")


    def test_create_args(self):
        y = SimpleModel.objects.language('nl').create(tr_title='TRANS_TITLE')
        self.assertEqual(y.get_current_language(), 'nl')
        self.assertEqual(y.tr_title, "TRANS_TITLE")


    def test_save_multiple(self):
        """
        Test the save_translations() function to store multiple languages.
        """
        x = SimpleModel()
        x.set_current_language('en')
        x.tr_title = "TITLE_EN"
        x.set_current_language('fr')
        x.tr_title = "TITLE_FR"
        x.set_current_language('es')
        x.tr_title = "TITLE_ES"
        x.set_current_language('nl')
        x.tr_title = "TITLE_NL"

        x.save()

        # Check if all translations are saved.
        self.assertEqual(sorted(x.translations.values_list('tr_title', flat=True)), ['TITLE_EN', 'TITLE_ES', 'TITLE_FR', 'TITLE_NL'])
        self.assertEqual(sorted(x.get_available_languages()), ['en', 'es', 'fr', 'nl'])
        self.assertTrue(x.has_translation('en'))
        self.assertTrue(x.has_translation('es'))
        self.assertFalse(x.has_translation('fi'))

        # Update 2 translations.
        # Only those should be updated in the database.
        x.set_current_language('es')
        x.tr_title = "TITLE_ES2"
        x.set_current_language('nl')
        x.tr_title = "TITLE_NL2"

        self.assertNumQueries(2, x.save_translations())

        # Any unmodified language is not saved.
        x.set_current_language('it', initialize=True)
        self.assertTrue(x.has_translation('it'))  # does return true for this object.
        self.assertNumQueries(0, x.save_translations())
        self.assertEqual(sorted(x.get_available_languages()), ['en', 'es', 'fr', 'nl'])


    def test_empty_model(self):
        """
        Test whether a translated model without any fields still works.
        """
        x = EmptyModel()
        x.set_current_language('en', initialize=True)
        x.set_current_language('fr', initialize=True)
        x.set_current_language('es')
        x.set_current_language('nl', initialize=True)
        x.save()

        self.assertEqual(sorted(x.get_available_languages()), ['en', 'fr', 'nl'])


    def test_create_translation(self):
        x = SimpleModel.objects.create()
        x.create_translation('en', tr_title='TITLE_EN')
        x.create_translation('fr', tr_title='TITLE_FR')

        self.assertEqual(sorted(x.get_available_languages()), ['en', 'fr'])


    def test_fallback_language(self):
        """
        Test whether the fallback language will be returned.
        """
        x = SimpleModel()
        x.set_current_language(self.conf_fallback)
        x.tr_title = "TITLE_FALLBACK"

        x.set_current_language(self.other_lang1)
        x.tr_title = 'TITLE_XX'
        x.save()

        with translation.override(self.other_lang2):
            x = SimpleModel.objects.get(pk=x.pk)
            self.assertEqual(x.tr_title, 'TITLE_FALLBACK')

    def test_fallback_language_no_current(self):
        """
        Test whether the fallback language will be returned,
        even when the current language does not have a translation.
        """
        x = SimpleModel()
        x.set_current_language(self.conf_fallback)
        x.tr_title = "TITLE_FALLBACK"

        self.assertEqual(
            x.safe_translation_getter('tr_title', language_code=self.other_lang1),
            'TITLE_FALLBACK')

    def test_any_fallback_model(self):
        """
        Test whether a failure in the fallback language can return any saved language (if configured for it).
        """
        x = AnyLanguageModel()
        x.set_current_language(self.other_lang1)
        x.tr_title = "TITLE_XX"

        x.save()

        with translation.override(self.other_lang2):
            x = AnyLanguageModel.objects.get(pk=x.pk)
            self.assertRaises(TranslationDoesNotExist, lambda: x._get_translated_model(use_fallback=True))
            self.assertEqual(x.tr_title, 'TITLE_XX')  # Even though there is no current language, there is a value.

            self.assertNumQueries(0, lambda: x._get_any_translated_model())   # Can fetch from cache next time.
            self.assertEqual(x._get_any_translated_model().language_code, self.other_lang1)


    def test_any_fallback_function(self):
        x = SimpleModel()
        x.set_current_language(self.other_lang1)
        x.tr_title = "TITLE_XX"

        x.save()

        with translation.override(self.other_lang2):
            x = SimpleModel.objects.get(pk=x.pk)
            self.assertRaises(TranslationDoesNotExist, lambda: x._get_translated_model(use_fallback=True))
            self.assertIs(x.safe_translation_getter('tr_title', 'DEFAULT'), 'DEFAULT')  # No lanuage, gives default
            self.assertEqual(x.safe_translation_getter('tr_title', any_language=True), 'TITLE_XX')  # Even though there is no current language, there is a value.

            self.assertNumQueries(0, lambda: x._get_any_translated_model())   # Can fetch from cache next time.
            self.assertEqual(x._get_any_translated_model().language_code, self.other_lang1)

    def test_save_ignore_fallback_marker(self):
        """
        Test whether the ``save_translations()`` method skips fallback languages
        """
        x = SimpleModel()
        x.set_current_language(self.other_lang1)
        x.tr_title = "TITLE_XX"
        x.set_current_language(self.other_lang2)       
        # try fetching, causing an fallback marker
        x.safe_translation_getter('tr_title', any_language=True)
        # Now save. This should not raise errors
        x.save()

    def test_model_with_zero_pk(self):
        """
        tests that the translated model is returned also when the pk is 0
        """
        x = SimpleModel()
        x.set_current_language(self.other_lang1)
        x.pk = 0
        x.tr_title = "EMPTY_PK"	

        x.save()
        
        # now fetch it from db
        try:
            SimpleModel.objects.get(pk=x.pk)
        except TranslationDoesNotExist:
            self.fail("zero pk is not supported!")
