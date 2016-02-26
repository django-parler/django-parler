from django.conf.urls import url
from .views import ArticleListView, ArticleDetailView

urlpatterns = [
    url(r'^$', ArticleListView.as_view(), name='article-list'),
    url(r'^(?P<slug>[^/]+)/$', ArticleDetailView.as_view(), name='article-details'),
]
