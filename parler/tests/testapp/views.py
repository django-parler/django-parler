from django.http import HttpResponse
from django.views.generic import DetailView
from parler.views import TranslatableSlugMixin
from .models import ArticleSlugModel


class ArticleSlugView(TranslatableSlugMixin, DetailView):
    model = ArticleSlugModel
    slug_field = 'slug'

    def render_to_response(self, context, **response_kwargs):
        return HttpResponse('view: {0}'.format(context['object'].slug))
