from django.conf.urls.i18n import i18n_patterns

# To intru
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .views import ArticleSlugView


class PasswordResetForm(auth_forms.PasswordResetForm):
    pass


urls = [
    path("article/<slug>/", ArticleSlugView.as_view(), name="article-slug-test-view"),
    # An URL with view-kwargs
    path(
        "tests/kwargs-view/",
        auth_views.PasswordResetView.as_view(),
        {
            "password_reset_form": PasswordResetForm,
            "post_reset_redirect": reverse_lazy("password-reset-done"),
        },
        name="view-kwargs-test-view",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password-reset-done",
    ),
]

urlpatterns = i18n_patterns(*urls)
