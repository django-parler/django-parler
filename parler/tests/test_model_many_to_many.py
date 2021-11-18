from .testapp.models import (
    ManyToManyAndOtherFieldsTranslationModel,
    ManyToManyOnlyFieldsTranslationModel,
    RegularModel,
)
from .utils import AppTestCase


class ModelManyToManyTestCase(AppTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.regular_one = RegularModel.objects.create(original_field="One")
        cls.regular_two = RegularModel.objects.create(original_field="Two")

    def test_save_many_to_many_only(self):
        """Test a model that has *only* translated many to many fields."""
        obj = ManyToManyOnlyFieldsTranslationModel.objects.create(shared="One")

        # Set many to many for English
        obj.set_current_language("en")
        obj.create_translation("en")
        obj.translated_many_to_many.set([self.regular_one])
        obj.save()
        self.assertEqual(
            ManyToManyOnlyFieldsTranslationModel.objects.language("en")
            .first()
            .translated_many_to_many.all()[0],
            self.regular_one,
        )

        # Set many to many for French
        obj.set_current_language("fr")
        obj.create_translation("fr")
        obj.translated_many_to_many.set([self.regular_two])
        obj.save()
        self.assertEqual(
            ManyToManyOnlyFieldsTranslationModel.objects.language("fr")
            .first()
            .translated_many_to_many.all()[0],
            self.regular_two,
        )

        # Check fallback
        self.assertEqual(
            ManyToManyOnlyFieldsTranslationModel.objects.language("nl")
            .first()
            .translated_many_to_many.all()[0],
            self.regular_one,
        )

    def test_save_many_to_many_and_other_fields(self):
        """Test a model that has *only* translated many to many fields."""
        obj = ManyToManyAndOtherFieldsTranslationModel.objects.create(shared="One")

        # Set many to many for English
        obj.set_current_language("en")
        obj.tr_title = "English"
        obj.save()
        obj.translated_many_to_many.set([self.regular_one])
        obj.save()
        self.assertEqual(
            ManyToManyAndOtherFieldsTranslationModel.objects.language("en")
            .first()
            .translated_many_to_many.all()[0],
            self.regular_one,
        )

        # Set many to many for French
        obj.set_current_language("fr")
        obj.tr_title = "French"
        obj.save()
        obj.translated_many_to_many.set([self.regular_two])
        obj.save()
        self.assertEqual(
            ManyToManyAndOtherFieldsTranslationModel.objects.language("fr")
            .first()
            .translated_many_to_many.all()[0],
            self.regular_two,
        )

        # Check fallback
        self.assertEqual(
            ManyToManyAndOtherFieldsTranslationModel.objects.language("nl")
            .first()
            .translated_many_to_many.all()[0],
            self.regular_one,
        )
