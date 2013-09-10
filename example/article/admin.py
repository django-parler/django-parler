from django.contrib import admin
from django.contrib.admin.widgets import AdminTextInputWidget, AdminTextareaWidget
from parler.admin import TranslatableAdmin
from .models import Article
from parler.forms import TranslatableModelForm, TranslatedField


# Example, translated fields can be enhanced by manually declaring them:
class ArticleAdminForm(TranslatableModelForm):
    title = TranslatedField(widget=AdminTextInputWidget)
    content = TranslatedField(widget=AdminTextareaWidget)


class ArticleAdmin(TranslatableAdmin):
    # Example form usage. This is optional.
    form = ArticleAdminForm


    def get_prepopulated_fields(self, request, obj=None):
        # Can't use prepopulated_fields= yet, but this is a workaround.
        return {'slug': ('title',)}


    # NOTE: when using Django 1.4, use declared_fieldsets= instead of fieldsets=
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'published'),
        }),
        ("Contents", {
            'fields': ('content',),
        })
    )


admin.site.register(Article, ArticleAdmin)
