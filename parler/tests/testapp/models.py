from __future__ import unicode_literals
from django.core.urlresolvers import reverse
from django.db import models
from parler.fields import TranslatedField
from parler.models import TranslatableModel, TranslatedFields, TranslatedFieldsModel
from parler.utils.context import switch_language


class ManualModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

class ManualModelTranslations(TranslatedFieldsModel):
    master = models.ForeignKey(ManualModel, related_name='translations')
    tr_title = models.CharField(max_length=200)


class SimpleModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

    translations = TranslatedFields(
        tr_title = models.CharField("Translated Title", max_length=200)
    )

    def __unicode__(self):
        return self.tr_title


class AnyLanguageModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')
    tr_title = TranslatedField(any_language=True)

    translations = TranslatedFields(
        tr_title = models.CharField(max_length=200)
    )

    def __unicode__(self):
        return self.tr_title



class EmptyModel(TranslatableModel):
    shared = models.CharField(max_length=200, default='')

    # Still tracks how many languages there are, but no actual translated fields exist yet.
    # This is useful when the model is a parent object for inlines. The parent model defines the language tabs.
    translations = TranslatedFields()

    def __unicode__(self):
        return self.shared


class ArticleSlugModel(TranslatableModel):
    translations = TranslatedFields(
        slug = models.SlugField()
    )

    def __unicode__(self):
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
    master = models.ForeignKey(DoubleModel, related_name='base_translations')
    l1_title = models.CharField(max_length=200)


class DoubleModelMoreTranslations(TranslatedFieldsModel):
    master = models.ForeignKey(DoubleModel, related_name='more_translations')
    l2_title = models.CharField(max_length=200)


class RegularModel(models.Model):
    # Normal model without translations. Test how replacing the field works.
    original_field = models.CharField(default="untranslated", max_length=255)


class CharModel(TranslatableModel):
    id = models.CharField(max_length=45, primary_key=True)


class CharModelTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(CharModel)
    tr_title = models.CharField(max_length=200)


class ForeignKeyTranslationModel(TranslatableModel):
    translations = TranslatedFields(
        translated_foreign = models.ForeignKey('RegularModel'),
    )
    shared = models.CharField(max_length=200)