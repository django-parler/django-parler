from __future__ import unicode_literals
from django.db import models
from django.urls import reverse
from parler.models import TranslatableModel, TranslatedFields
from parler.utils.context import switch_language


class Article(TranslatableModel):
    """
    Example translatable model.
    """

    # The translated fields:
    translations = TranslatedFields(
        title = models.CharField("Title", max_length=200),
        slug = models.SlugField("Slug"),
        content = models.TextField(),

        # Make slug unique per language
        meta={
            'unique_together': (
                ('slug', 'language_code'),
            ),
        }
    )

    # Regular fields
    published = models.BooleanField("Is published", default=False)
    category = models.ForeignKey("Category", null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __str__(self):
        # Fetching the title just works, as all
        # attributes are proxied to the translated model.
        # Fallbacks are handled as well.
        return "{0}".format(self.title)

    def get_absolute_url(self):
        # The switch_language() is needed because we use the /##/ prefix by i18n_patterns()
        # If the language is part of the URL parameters, you can pass it directly off course.
        with switch_language(self):
            return reverse('article-details', kwargs={'slug': self.slug})

    def get_all_slugs(self):
        # Example illustration, how to fetch all slugs in a single query:
        return dict(self.translations.values_list('language_code', 'slug'))


class Category(models.Model):
    """
    Example model for inline edition of Articles
    """

    name = models.CharField("Name", max_length=200)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        # Fetching the title just works, as all
        # attributes are proxied to the translated model.
        # Fallbacks are handled as well.
        return "{0}".format(self.name)


class StackedCategory(Category):
    """
    Proxy model to demonstrate different admin settings.
    """

    class Meta:
        verbose_name = "Stacked Category"
        verbose_name_plural = "Stacked Categories"
        proxy = True


class TabularCategory(Category):
    """
    Proxy model to demonstrate different admin settings.
    """

    class Meta:
        verbose_name = "Tabular Category"
        verbose_name_plural = "Tabular Categories"
        proxy = True
