from django.conf.urls import *
from .views import ArticleListView, ArticleDetailView

urlpatterns = patterns('',
    url(r'^$', ArticleListView.as_view(), name='article-list'),
    url(r'^(?P<slug>[^/]+)/$', ArticleDetailView.as_view(), name='article-details'),
)
