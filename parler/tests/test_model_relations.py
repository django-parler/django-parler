from .testapp.models import (
    ForeignKeyTranslationModel,
    RegularModel,
    TranslationRelated,
    TranslationRelatedRelation,
)
from .utils import AppTestCase


class TranslationRelationTestCase(AppTestCase):
    def test_related_objects_in_translation_model(self):
        instance = TranslationRelated()
        instance.set_current_language(self.other_lang1)

        # This should not raise errors
        instance.title = "Title Lang1"
        instance.save()

        instance.set_current_language(self.other_lang2)

        # This should not raise errors
        instance.title = "Title Lang2"
        instance.save()

        translation1 = instance.get_translation(self.other_lang1)

        translation1.translation_relations.create(name="relation 1.1")
        translation1.translation_relations.create(name="relation 1.2")

        translation2 = instance.get_translation(self.other_lang2)
        translation2.translation_relations.create(name="relation 2.1")

        total_related_objects = TranslationRelatedRelation.objects.filter(
            translation__master=instance
        ).count()

        lang1_related_object = TranslationRelatedRelation.objects.filter(
            translation__language_code=self.other_lang1,
            translation__master=instance,
        ).count()

        lang2_related_objects = TranslationRelatedRelation.objects.filter(
            translation__language_code=self.other_lang2,
            translation__master=instance,
        ).count()

        self.assertEqual(3, total_related_objects)
        self.assertEqual(2, lang1_related_object)
        self.assertEqual(1, lang2_related_objects)

    def test_translation_is_modified(self):
        r1 = RegularModel.objects.create(original_field="r1")
        r2 = RegularModel.objects.create(original_field="r2")

        instance = ForeignKeyTranslationModel.objects.create(
            translated_foreign=r1,
            shared="shared",
        )
        translation = instance.get_translation(instance.language_code)

        self.assertFalse(translation.is_modified)

        instance.translated_foreign = r2
        translation = instance.get_translation(instance.language_code)

        self.assertTrue(translation.is_modified)
