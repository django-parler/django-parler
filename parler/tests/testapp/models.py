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
