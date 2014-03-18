import django
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse


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
