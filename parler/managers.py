"""
Custom generic managers
"""
from django.db import models
from django.db.models.query import QuerySet
from parler import appsettings



class TranslatableQuerySet(QuerySet):
    """
    An enhancement of the QuerySet which sets the objects language before they are returned.

    When using this method with *django-polymorphic*, make sure this
    class is first in the chain of inherited classes.
    """

    def __init__(self, *args, **kwargs):
        super(TranslatableQuerySet, self).__init__(*args, **kwargs)
        self._language = []


    def _clone(self, klass=None, setup=False, **kw):
        c = super(TranslatableQuerySet, self)._clone(klass, setup, **kw)
        c._language = self._language
        return c


    def language(self, language_code=None):
        """
        Set the language code to assign to objects retrieved using this QuerySet.
        """
        if language_code is None:
            language_code = appsettings.PARLER_DEFAULT_LANGUAGE_CODE

        self._language = language_code
        return self


    def iterator(self):
        """
        Overwritten iterator which will apply the decorate functions before returning it.
        """
        # Based on django-queryset-transform.
        # This object however, operates on a per-object instance
        # without breaking the result generators
        base_iterator = super(TranslatableQuerySet, self).iterator()
        for obj in base_iterator:
            # Apply the language setting.
            if self._language:
                obj.set_current_language(self._language)

            yield obj


class TranslatableManager(models.Manager):
    """
    The manager class which ensures the enhanced TranslatableQuerySet object is used.
    """
    def get_query_set(self, *args, **kwargs):
        return TranslatableQuerySet(self.model, *args, **kwargs)

    def language(self, language_code=None):
        """
        Set the language code to assign to objects retrieved using this Manager.
        """
        return self.get_query_set().language(language_code)


# Export the names in django-hvad style too:
TranslationQueryset = TranslatableQuerySet
TranslationManager = TranslatableManager
