from django.http import Http404
from django.utils.translation import get_language
from django.views.generic import ListView, DetailView
from .models import Article


class BaseArticleMixin(object):
    # Only show published articles.
    def get_queryset(self):
        return super(BaseArticleMixin, self).get_queryset().filter(published=True)


class ArticleListView(BaseArticleMixin, ListView):
    model = Article
    template_name = 'article/list.html'

    def get_queryset(self):
        # Only show objects translated in the current language.
        language = get_language()
        return super(ArticleListView, self).get_queryset().filter(translations__language_code=language)


class ArticleDetailView(BaseArticleMixin, DetailView):
    model = Article
    slug_field = 'translations__slug'
    template_name = 'article/details.html'  # This works as expected

    def get_object(self, queryset=None):
        slug = self.kwargs['slug']
        language = get_language()
        try:
            return self.get_queryset().get(translations__language_code=language, translations__slug=slug)
        except Article.DoesNotExist as e:
            raise Http404(e)
