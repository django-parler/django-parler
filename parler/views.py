import django
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.views import generic
from django.views.generic.edit import ModelFormMixin
from parler.forms import TranslatableModelForm
from parler.models import TranslatableModel
from parler.utils.views import get_language_parameter, get_language_tabs

__all__ = (
    'ViewUrlMixin',
    'TranslatableSingleObjectMixin',
    'TranslatableModelFormMixin',
    'TranslatableCreateView',
    'TranslatableUpdateView',
)


class ViewUrlMixin(object):
    """
    Provide a ``view.get_view_url`` method in the template.

    This tells the template what the exact canonical URL should be of a view.
    The ``get_translated_url`` template tag uses this to find the proper translated URL of the current page.
    """
    #: The default view name used by :func:`get_view_url`, which should correspond with the view name in the URLConf.
    view_url_name = None


    def get_view_url(self):
        """
        This method is used by the ``get_translated_url`` template tag.

        By default, it uses the :attr:`view_url_name` to generate an URL.
        Override this function in case the translated URL is a bit more complex.
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



class TranslatableSingleObjectMixin(object):
    """
    Mixin to add translation support to class based views.
    """
    query_language_key = 'language'


    def get_object(self, queryset=None):
        """
        Assign the language for the retrieved object.
        """
        object = super(TranslatableSingleObjectMixin, self).get_object(queryset)
        if isinstance(object, TranslatableModel):
            object.set_current_language(self._language(object), initialize=True)
        return object


    def _language(self, object=None):
        """
        Get the language parameter from the current request.
        """
        return get_language_parameter(self.request, self.query_language_key, object=object, default=self.get_default_language(object=object))


    def get_default_language(self, object=None):
        """
        Return the default language to use, if no language parameter is given.
        By default, it uses the default parler-language.
        """
        # Some users may want to override this, to return get_language()
        return None


class TranslatableModelFormMixin(TranslatableSingleObjectMixin):
    """
    Mixin to add translation support to class based views.
    """

    def get_form_class(self):
        """
        Return a ``TranslatableModelForm`` by default if no form_class is set.
        """
        super_method = super(TranslatableModelFormMixin, self).get_form_class
        if not (super_method.__func__ is ModelFormMixin.get_form_class.__func__):
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


    def get_form_language(self):
        """
        Return the current language for the currently displayed object fields.
        """
        if self.object is not None:
            return self.object.get_current_language()
        else:
            return self._language()


    def get_context_data(self, **kwargs):
        context = super(TranslatableModelFormMixin, self).get_context_data(**kwargs)
        context['language_tabs'] = self.get_language_tabs()
        return context


    def get_language_tabs(self):
        """
        Determine the language tabs to show.
        """
        current_language = self.get_form_language()
        if self.object:
            available_languages = list(self.object.get_available_languages())
        else:
            available_languages = []

        return get_language_tabs(self.request, current_language, available_languages)


# For the lazy ones:
class TranslatableCreateView(TranslatableModelFormMixin, generic.CreateView):
    """
    Create view that supports translated models.
    """
    pass


class TranslatableUpdateView(TranslatableModelFormMixin, generic.UpdateView):
    """
    Update view that supports translated models.
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
