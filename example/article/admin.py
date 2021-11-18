from django.contrib import admin
from django.contrib.admin.widgets import AdminTextareaWidget, AdminTextInputWidget

from parler.admin import TranslatableAdmin, TranslatableStackedInline, TranslatableTabularInline
from parler.forms import TranslatableModelForm, TranslatedField

from .models import Article, Category, StackedCategory, TabularCategory


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
    list_display = ("title", "language_column")
    list_filter = ("published",)

    # Example custom form usage.
    form = ArticleAdminForm

    fieldsets = (
        (
            None,
            {
                "fields": ("title", "slug", "published", "category"),
            },
        ),
        (
            "Contents",
            {
                "fields": ("content",),
            },
        ),
    )

    def get_prepopulated_fields(self, request, obj=None):
        # Can't use prepopulated_fields= yet, but this is a workaround.
        return {"slug": ("title",)}


class ArticleStacked(TranslatableStackedInline):
    model = Article
    extra = 1


class ArticleTabular(TranslatableTabularInline):
    model = Article
    extra = 1


class CategoryAdmin(admin.ModelAdmin):
    pass


class CategoryStackedAdmin(admin.ModelAdmin):

    inlines = [ArticleStacked]


class CategoryTabularAdmin(admin.ModelAdmin):

    inlines = [ArticleTabular]


admin.site.register(Article, ArticleAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(StackedCategory, CategoryStackedAdmin)
admin.site.register(TabularCategory, CategoryTabularAdmin)
