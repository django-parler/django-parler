"""
The views provide high-level utilities to integrate translation support into other projects.

The following mixins are available:

* :class:`ViewUrlMixin` - provide a ``get_view_url`` for the :ref:`{% get_translated_url %} <get_translated_url>` template tag.
* :class:`TranslatableSlugMixin` - enrich the :class:`~django.views.generic.detail.DetailView` to support translatable slugs.
* :class:`LanguageChoiceMixin` - add ``?language=xx`` support to a view (e.g. for editing).
* :class:`TranslatableModelFormMixin` - add support for translatable forms, e.g. for creating/updating objects.

The following views are available:

* :class:`TranslatableCreateView` - The :class:`~django.views.generic.edit.CreateView` with :class:`TranslatableModelFormMixin` support.
* :class:`TranslatableUpdateView` - The :class:`~django.views.generic.edit.UpdateView` with :class:`TranslatableModelFormMixin` support.
"""
from __future__ import unicode_literals
import django
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponsePermanentRedirect
from django.utils import translation
from django.views import generic
from django.views.generic.edit import ModelFormMixin
from parler.forms import TranslatableModelForm
from parler.models import TranslatableModel
from parler.utils import get_active_language_choices
from parler.utils.context import switch_language
from parler.utils.views import get_language_parameter, get_language_tabs

__all__ = (
    'ViewUrlMixin',
    'TranslatableSlugMixin',
    'LanguageChoiceMixin',
    'TranslatableModelFormMixin',
    'TranslatableCreateView',
    'TranslatableUpdateView',
)


class ViewUrlMixin(object):
    """
    Provide a ``view.get_view_url`` method in the template.

    This tells the template what the exact canonical URL should be of a view.
    The :ref:`{% get_translated_url %} <get_translated_url>` template tag uses this
    to find the proper translated URL of the current page.

    Typically, setting the :attr:`view_url_name` just works::

        class ArticleListView(ViewUrlMixin, ListView):
            view_url_name = 'article:list'

    The :func:`get_view_url` will use the :attr:`view_url_name` together
    with ``view.args`` and ``view.kwargs`` construct the URL.
    When some arguments are translated (e.g. a slug), the :func:`get_view_url`
    can be overwritten to generate the proper URL::

        from parler.views import ViewUrlMixin, TranslatableUpdateView
        from parler.utils.context import switch_language

        class ArticleEditView(ViewUrlMixin, TranslatableUpdateView):
            view_url_name = 'article:edit'

            def get_view_url(self):
                with switch_language(self.object, get_language()):
                    return reverse(self.view_url_name, kwargs={'slug': self.object.slug})
    """
    #: The default view name used by :func:`get_view_url`, which
    #: should correspond with the view name in the URLConf.
    view_url_name = None


    def get_view_url(self):
        """
        This method is used by the ``get_translated_url`` template tag.

        By default, it uses the :attr:`view_url_name` to generate an URL.
        When the URL ``args`` and ``kwargs`` are translatable,
        override this function instead to generate the proper URL.
        """
        if not self.view_url_name:
            # Sadly, class based views can't work with reverse(func_pointer) as that's unknown.
            # Neither is it possible to use resolve(self.request.path).view_name in this function as auto-detection.
            # This function can be called in the context of a different language.
            # When i18n_patterns() is applied, that resolve() will fail.
            #
            # Hence, you need to provide a "view_url_name" as static configuration option.
            raise ImproperlyConfigured("Missing `view_url_name` attribute on {0}".format(self.__class__.__name__))

        return reverse(self.view_url_name, args=self.args, kwargs=self.kwargs)


    if django.VERSION < (1,5):
        # The `get_translated_url` tag relies on the fact that the template can access the view again.
        # This was not possible until Django 1.5, so provide the `ContextMixin` logic for earlier Django versions.

        def get_context_data(self, **kwargs):
            if 'view' not in kwargs:
                kwargs['view'] = self
            return kwargs


class TranslatableSlugMixin(object):
    """
    An enhancement for the :class:`~django.views.generic.DetailView` to deal with translated slugs.
    This view makes sure that:

    * The object is fetched in the proper translation.
    * The slug field is read from the translation model, instead of the shared model.
    * Fallback languages are handled.
    * Objects are not accidentally displayed in their fallback slug, but redirect to the translated slug.

    Example:

    .. code-block:: python

        class ArticleDetailView(TranslatableSlugMixin, DetailView):
            model = Article
            template_name = 'article/details.html'
    """
    def get_translated_filters(self, slug):
        """
        Allow passing other filters for translated fields.
        """
        return {
            self.get_slug_field(): slug
        }

    def get_language(self):
        """
        Define the language of the current view, defaults to the active language.
        """
        return translation.get_language()

    def get_language_choices(self):
        """
        Define the language choices for the view, defaults to the defined settings.
        """
        return get_active_language_choices(self.get_language())

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(TranslatableSlugMixin, self).dispatch(request, *args, **kwargs)
        except FallbackLanguageResolved as e:
            # Handle the fallback language redirect for get_object()
            with switch_language(e.object, e.correct_language):
                return HttpResponsePermanentRedirect(e.object.get_absolute_url())

    def get_object(self, queryset=None):
        """
        Fetch the object using a translated slug.
        """
        if queryset is None:
            queryset = self.get_queryset()

        slug = self.kwargs[self.slug_url_kwarg]
        choices = self.get_language_choices()

        obj = None
        using_fallback = False
        prev_choices = []
        for lang_choice in choices:
            try:
                # Get the single item from the filtered queryset
                # NOTE. Explicitly set language to the state the object was fetched in.
                filters = self.get_translated_filters(slug=slug)
                obj = queryset.translated(lang_choice, **filters).language(lang_choice).get()
            except ObjectDoesNotExist:
                # Translated object not found, next object is marked as fallback.
                using_fallback = True
                prev_choices.append(lang_choice)
            else:
                break

        if obj is None:
            tried_msg = ", tried languages: {0}".format(", ".join(choices))
            error_message = translation.ugettext("No %(verbose_name)s found matching the query") % {'verbose_name': queryset.model._meta.verbose_name}
            raise Http404(error_message + tried_msg)

        # Object found!
        if using_fallback:
            # It could happen that objects are resolved using their fallback language,
            # but the actual translation also exists. Either that means this URL should
            # raise a 404, or a redirect could be made as service to the users.
            # It's possible that the old URL was active before in the language domain/subpath
            # when there was no translation yet.
            for prev_choice in prev_choices:
                if obj.has_translation(prev_choice):
                    # Only dispatch() and render_to_response() can return a valid response,
                    # By breaking out here, this functionality can't be broken by users overriding render_to_response()
                    raise FallbackLanguageResolved(obj, prev_choice)

        return obj


class FallbackLanguageResolved(Exception):
    """
    An object was resolved in the fallback language, while it could be in the normal language.
    This exception is used internally to control code flow.
    """
    def __init__(self, object, correct_language):
        self.object = object
        self.correct_language = correct_language



class LanguageChoiceMixin(object):
    """
    Mixin to add language selection support to class based views, particularly create and update views.
    It adds support for the ``?language=..`` parameter in the query string, and tabs in the context.
    """
    query_language_key = 'language'


    def get_object(self, queryset=None):
        """
        Assign the language for the retrieved object.
        """
        object = super(LanguageChoiceMixin, self).get_object(queryset)
        if isinstance(object, TranslatableModel):
            object.set_current_language(self.get_language(), initialize=True)
        return object


    def get_language(self):
        """
        Get the language parameter from the current request.
        """
        return get_language_parameter(self.request, self.query_language_key, default=self.get_default_language(object=object))


    def get_default_language(self, object=None):
        """
        Return the default language to use, if no language parameter is given.
        By default, it uses the default parler-language.
        """
        # Some users may want to override this, to return get_language()
        return None


    def get_current_language(self):
        """
        Return the current language for the currently displayed object fields.
        This reads ``self.object.get_current_language()`` and falls back to :func:`get_language`.
        """
        if self.object is not None:
            return self.object.get_current_language()
        else:
            return self.get_language()


    def get_context_data(self, **kwargs):
        context = super(LanguageChoiceMixin, self).get_context_data(**kwargs)
        context['language_tabs'] = self.get_language_tabs()
        return context


    def get_language_tabs(self):
        """
        Determine the language tabs to show.
        """
        current_language = self.get_current_language()
        if self.object:
            available_languages = list(self.object.get_available_languages())
        else:
            available_languages = []

        return get_language_tabs(self.request, current_language, available_languages)


class TranslatableModelFormMixin(LanguageChoiceMixin):
    """
    Mixin to add translation support to class based views.

    For example, adding translation support to django-oscar::

        from oscar.apps.dashboard.catalogue import views as oscar_views
        from parler.views import TranslatableModelFormMixin

        class ProductCreateUpdateView(TranslatableModelFormMixin, oscar_views.ProductCreateUpdateView):
            pass
    """

    def get_form_class(self):
        """
        Return a ``TranslatableModelForm`` by default if no form_class is set.
        """
        super_method = super(TranslatableModelFormMixin, self).get_form_class
        # no "__func__" on the class level function in python 3
        default_method = getattr(ModelFormMixin.get_form_class, '__func__', ModelFormMixin.get_form_class)
        if not (super_method.__func__ is default_method):
            # Don't get in your way, if you've overwritten stuff.
            return super_method()
        else:
            # Same logic as ModelFormMixin.get_form_class, but using the right form base class.
            if self.form_class:
                return self.form_class
            else:
                model = _get_view_model(self)
                return modelform_factory(model, form=TranslatableModelForm)


    def get_form_kwargs(self):
        """
        Pass the current language to the form.
        """
        kwargs = super(TranslatableModelFormMixin, self).get_form_kwargs()
        # The TranslatableAdmin can set form.language_code, because the modeladmin always creates a fresh subclass.
        # If that would be done here, the original globally defined form class would be updated.
        kwargs['_current_language'] = self.get_form_language()
        return kwargs


    # Backwards compatibility
    # Make sure overriding get_current_language() affects get_form_language() too.
    def get_form_language(self):
        return self.get_current_language()


# For the lazy ones:
class TranslatableCreateView(TranslatableModelFormMixin, generic.CreateView):
    """
    Create view that supports translated models.
    This is a mix of the :class:`TranslatableModelFormMixin`
    and Django's :class:`~django.views.generic.edit.CreateView`.
    """
    pass


class TranslatableUpdateView(TranslatableModelFormMixin, generic.UpdateView):
    """
    Update view that supports translated models.
    This is a mix of the :class:`TranslatableModelFormMixin`
    and Django's :class:`~django.views.generic.edit.UpdateView`.
    """
    pass



def _get_view_model(self):
    if self.model is not None:
        # If a model has been explicitly provided, use it
        return self.model
    elif hasattr(self, 'object') and self.object is not None:
        # If this view is operating on a single object, use the class of that object
        return self.object.__class__
    else:
        # Try to get a queryset and extract the model class from that
        return self.get_queryset().model


# Backwards compatibility
TranslatableSingleObjectMixin = LanguageChoiceMixin
