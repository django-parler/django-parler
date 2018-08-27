from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from parler.fields import TranslatedField
from parler.managers import LightTranslatableManager, DeepTranslatableManager, AutoAddTranslationsManager
from parler.models import TranslatableModel, TranslatedFields, TranslatedFieldsModel
from parler.utils.context import switch_language

try:
    from django.urls import reverse
except ImportError:
    # Django <= 1.10
    from django.core.urlresolvers import reverse


class ManualModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')


class ManualModelTranslations(TranslatedFieldsModel):
    master = models.ForeignKey(ManualModel, related_name='translations', on_delete=models.CASCADE)
    tr_title = models.CharField(max_length=200)


@python_2_unicode_compatible
class SimpleModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

    translations = TranslatedFields(
        tr_title = models.CharField("Translated Title", max_length=200)
    )

    def __str__(self):
        return self.tr_title


@python_2_unicode_compatible
class SimpleLightModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

    translations = TranslatedFields(
        tr_title = models.CharField("Translated Title", max_length=200)
    )

    objects = LightTranslatableManager()

    def __str__(self):
        return self.tr_title


@python_2_unicode_compatible
class SimpleModelA(TranslatableModel):
    translations = TranslatedFields(
        model_a_title = models.CharField("ModelA Translated Title", max_length=200)
    )

    def __str__(self):
        return self.model_a_title


@python_2_unicode_compatible
class SimpleModelB(TranslatableModel):
    model_a = models.ForeignKey(SimpleModelA, on_delete=models.CASCADE)

    translations = TranslatedFields(
        model_b_title = models.CharField("ModelB Translated Title", max_length=200)
    )

    def __str__(self):
        return self.model_b_title


@python_2_unicode_compatible
class SimpleModelC(TranslatableModel):
    model_b = models.ForeignKey(SimpleModelB, on_delete=models.CASCADE)

    translations = TranslatedFields(
        model_c_title = models.CharField("ModelC Translated Title", max_length=200)
    )

    objects = DeepTranslatableManager()

    def __str__(self):
        return self.model_c_title


@python_2_unicode_compatible
class SimpleNonTranslatableModelC(models.Model):
    model_b = models.ForeignKey(SimpleModelB, on_delete=models.CASCADE)

    model_c_title = models.CharField("ModelC Translated Title", max_length=200)

    objects = AutoAddTranslationsManager()

    def __str__(self):
        return self.model_c_title


class CleanCharField(models.CharField):

    def clean(self, value, model_instance):
        super(CleanCharField, self).clean(value, model_instance)
        return value + "_cleanchar"


@python_2_unicode_compatible
class CleanFieldModel(TranslatableModel):
    shared = CleanCharField(max_length=200, default='')
    tr_title = TranslatedField()

    def __str__(self):
        return self.tr_title

    def clean(self):
        self.shared += "_cleanshared"


class CleanFieldModelTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(
        CleanFieldModel, related_name='translations', null=True,
        default=1, on_delete=models.CASCADE)
    tr_title = CleanCharField("Translated Title", max_length=200)

    class Meta:
        unique_together = ('language_code', 'master')

    def clean(self):
        self.tr_title += "_cleantrans"


@python_2_unicode_compatible
class DateTimeModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')
    datetime = models.DateTimeField()

    translations = TranslatedFields(
        tr_title=models.CharField("Translated Title", max_length=200)
    )

    def __str__(self):
        return self.tr_title


@python_2_unicode_compatible
class AnyLanguageModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')
    tr_title = TranslatedField(any_language=True)

    translations = TranslatedFields(
        tr_title = models.CharField(max_length=200)
    )

    def __str__(self):
        return self.tr_title


@python_2_unicode_compatible
class NotRequiredModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

    translations = TranslatedFields(
        tr_title = models.CharField(max_length=200, default='DEFAULT_TRANS_TITLE')
    )

    def __str__(self):
        return self.tr_title


@python_2_unicode_compatible
class EmptyModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

    # Still tracks how many languages there are, but no actual translated fields exist yet.
    # This is useful when the model is a parent object for inlines. The parent model defines the language tabs.
    translations = TranslatedFields()

    def __str__(self):
        return self.shared


@python_2_unicode_compatible
class ArticleSlugModel(TranslatableModel):
    translations = TranslatedFields(
        slug = models.SlugField()
    )

    def __str__(self):
        return self.slug

    def get_absolute_url(self):
        with switch_language(self):
            return reverse('article-slug-test-view', kwargs={'slug': self.slug})


class AbstractModel(TranslatableModel):
    # Already declared, but not yet linkable to a TranslatedFieldsModel
    tr_title = TranslatedField(any_language=True)

    class Meta:
        abstract = True


class ConcreteModel(AbstractModel):
    translations = TranslatedFields(
        tr_title = models.CharField("Translated Title", max_length=200)
    )


class UniqueTogetherModel(TranslatableModel):
    translations = TranslatedFields(
        slug = models.SlugField(),
        meta = {
            'unique_together': [
                ('slug', 'language_code',),
            ]
        }
    )


class Level1(TranslatableModel):
    l1_translations = TranslatedFields(
        l1_title = models.CharField(max_length=200)
    )


class Level2(Level1):
    l2_translations = TranslatedFields(
        l2_title = models.CharField(max_length=200)
    )


class ProxyBase(TranslatableModel):
    base_translations = TranslatedFields(
        base_title = models.CharField(max_length=200)
    )


class ProxyModel(ProxyBase):
    proxy_translations = TranslatedFields(
        proxy_title = models.CharField(max_length=200)
    )

    class Meta:
        proxy = True


class DoubleModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')


class DoubleModelTranslations(TranslatedFieldsModel):
    master = models.ForeignKey(DoubleModel, related_name='base_translations', on_delete=models.CASCADE)
    l1_title = models.CharField(max_length=200)


class DoubleModelMoreTranslations(TranslatedFieldsModel):
    master = models.ForeignKey(DoubleModel, related_name='more_translations', on_delete=models.CASCADE)
    l2_title = models.CharField(max_length=200)


class RegularModel(models.Model):
    # Normal model without translations. Test how replacing the field works.
    original_field = models.CharField(default="untranslated", max_length=255)


class CharModel(TranslatableModel):
    id = models.CharField(max_length=45, primary_key=True)


class CharModelTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(CharModel, on_delete=models.CASCADE)
    tr_title = models.CharField(max_length=200)


class ForeignKeyTranslationModel(TranslatableModel):
    translations = TranslatedFields(
        translated_foreign = models.ForeignKey('RegularModel', on_delete=models.CASCADE),
    )
    shared = models.CharField(max_length=200)


class TranslationRelated(TranslatableModel):
    shared = models.CharField(max_length=200)
    translation_relations = TranslatedField()


class TranslationRelatedTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(TranslationRelated, related_name='translations', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    m2m_regular = models.ManyToManyField(RegularModel)


class TranslationRelatedRelation(models.Model):
    translation = models.ForeignKey(TranslationRelatedTranslation, related_name='translation_relations', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
