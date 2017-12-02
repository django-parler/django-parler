import django
from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from .views import ArticleSlugView

# To intru
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import views as auth_views

try:
    from django.urls import reverse_lazy
except ImportError:
    # Support for Django <= 1.10
    from django.core.urlresolvers import reverse_lazy


class PasswordResetForm(auth_forms.PasswordResetForm):
    pass


urls = [
    url(r'article/(?P<slug>[^\/]+)/$', ArticleSlugView.as_view(), name='article-slug-test-view'),

    # An URL with view-kwargs
    url(
        r'^tests/kwargs-view/$', auth_views.password_reset, {
            'password_reset_form': PasswordResetForm,
            'post_reset_redirect': reverse_lazy('password-reset-done')
        },
        name='view-kwargs-test-view'
    ),
    url(r'^password-reset/done/$', auth_views.password_reset_done, name='password-reset-done'),
]

if django.VERSION >= (1, 8):
    # New style without prefix
    urlpatterns = i18n_patterns(*urls)
else:
    urlpatterns = i18n_patterns('', *urls)
