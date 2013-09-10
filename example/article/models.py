from django.core.urlresolvers import reverse
from django.utils import translation
from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class Article(TranslatableModel):
    """
    Example translatable model.
    """

    # The translated fields:
    translations = TranslatedFields(
        title = models.CharField("Title", max_length=200),
        slug = models.SlugField("Slug", unique=True),
        content = models.TextField()
    )

    # Regular fields
    published = models.BooleanField("Is published", default=False)

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __unicode__(self):
        # Fetching the title just works, as all
        # attributes are proxied to the translated model.
        # Fallbacks are handled as well.
        return self.title

    def get_absolute_url(self):
        # The override is only needed because we use the /##/ prefix by i18n_patterns()
        # If the language is part of the URL parameters, you can pass it directly off course.
        with translation.override(self.get_current_language()):
            return reverse('article-details', kwargs={'slug': self.slug})

    def get_all_slugs(self):
        # Example illustration, how to fetch all slugs in a single query:
        return dict(self.translations.values_list('language_code', 'slug'))
