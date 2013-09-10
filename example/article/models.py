from django.core.urlresolvers import reverse
from django.utils import translation
from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class Article(TranslatableModel):
    # In this case, all fields are translated.
    translations = TranslatedFields(
        title = models.CharField("Title", max_length=200),
        slug = models.SlugField("Slug", unique=True),
        content = models.TextField()
    )

    published = models.BooleanField("Is published", default=False)

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        with translation.override(self.get_current_language()):  # Only needed because we use the /##/ prefix by i18n_patterns()
            return reverse('article-details', kwargs={'slug': self.slug})

    # Example illustration, how to fetch all slugs in a single query:
    def get_all_slugs(self):
        return dict(self.translations.values_list('language_code', 'slug'))
