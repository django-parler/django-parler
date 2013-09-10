from django.contrib import admin
from django.contrib.admin.widgets import AdminTextInputWidget, AdminTextareaWidget
from parler.admin import TranslatableAdmin
from .models import Article
from parler.forms import TranslatableModelForm, TranslatedField


class ArticleAdminForm(TranslatableModelForm):
    """
    Example form

    Translated fields can be enhanced by manually declaring them:
    """
    title = TranslatedField(widget=AdminTextInputWidget)
    content = TranslatedField(widget=AdminTextareaWidget)


class ArticleAdmin(TranslatableAdmin):
    """
    Example admin.

    Using an empty class would already work,
    but this example shows some additional options.
    """

    # The 'language_column' is provided by the base class:
    list_display = ('title', 'language_column')

    # Example custom form usage.
    form = ArticleAdminForm

    # NOTE: when using Django 1.4, use declared_fieldsets= instead of fieldsets=
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'published'),
        }),
        ("Contents", {
            'fields': ('content',),
        })
    )

    def get_prepopulated_fields(self, request, obj=None):
        # Can't use prepopulated_fields= yet, but this is a workaround.
        return {'slug': ('title',)}



admin.site.register(Article, ArticleAdmin)
