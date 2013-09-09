"""
Custom generic managers
"""
from django.db import models
from django.db.models.query import QuerySet


# Based on django-queryset-transform.
# This object however, operates on a per-object instance
# without breaking the result generators
from parler import appsettings


class TranslatedQuerySet(QuerySet):
    """
    An enhancement of the QuerySet which allows objects to be decorated
    with extra properties before they are returned.

    When using this method with *django-polymorphic*, make sure this
    class is first in the chain of inherited classes.
    """

    def __init__(self, *args, **kwargs):
        super(TranslatedQuerySet, self).__init__(*args, **kwargs)
        self._language = []


    def _clone(self, klass=None, setup=False, **kw):
        c = super(TranslatedQuerySet, self)._clone(klass, setup, **kw)
        c._language = self._language
        return c


    def language(self, language_code=None):
        """
        Register a function which will decorate a retrieved object before it's returned.
        """
        if language_code is None:
            language_code = appsettings.PARLER_DEFAULT_LANGUAGE_CODE

        self._language = language_code
        return self


    def iterator(self):
        """
        Overwritten iterator which will apply the decorate functions before returning it.
        """
        base_iterator = super(TranslatedQuerySet, self).iterator()
        for obj in base_iterator:
            # Apply the language setting.
            if self._language:
                obj.set_current_language(self._language)

            yield obj


class TranslatedManager(models.Manager):
    """
    The manager class which ensures the enhanced TranslatedQuerySet object is used.
    """
    def get_query_set(self, *args, **kwargs):
        return TranslatedQuerySet(self.model, *args, **kwargs)
