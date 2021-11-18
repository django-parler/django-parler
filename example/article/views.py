from django.utils.translation import get_language
from django.views.generic import DetailView, ListView

from parler.views import TranslatableSlugMixin

from .models import Article


class BaseArticleMixin:
    # Only show published articles.

    def get_queryset(self):
        return super().get_queryset().filter(published=True)


class ArticleListView(BaseArticleMixin, ListView):
    model = Article
    template_name = "article/list.html"

    def get_queryset(self):
        # Only show objects translated in the current language.
        language = get_language()
        return super().get_queryset().filter(translations__language_code=language)


class ArticleDetailView(BaseArticleMixin, TranslatableSlugMixin, DetailView):
    model = Article
    template_name = "article/details.html"  # This works as expected
