"""
Custom generic managers
"""
import django
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q
from django.db.models.query import FilteredRelation, ModelIterable, QuerySet
from django.utils.translation import get_language

from parler import appsettings
from parler.utils import get_active_language_choices
from parler.utils.db import get_related_translation_annotation_name


class TranslatableQuerySet(QuerySet):
    """
    An enhancement of the QuerySet which sets the objects language before they are returned.

    When using this class in combination with *django-polymorphic*, make sure this
    class is first in the chain of inherited classes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._language = None
        self._related_translation_annotations = set()

    def _clone(self):
        c = super()._clone()
        c._language = self._language
        c._related_translation_annotations = self._related_translation_annotations.copy()
        return c

    def create(self, **kwargs):
        # Pass language setting to the object, as people start assuming things
        # like .language('xx').create(..) which is a nice API after all.
        if self._language:
            kwargs["_current_language"] = self._language
        return super().create(**kwargs)

    def _fetch_all(self):
        # Make sure the current language is assigned when Django fetches the data.
        # This low-level method is overwritten as that works better across Django versions.
        # Alternatives includes hacking the _iterable_class, which breaks django-polymorphic
        super()._fetch_all()
        if (
            self._language is not None
            and self._result_cache
            and isinstance(self._result_cache[0], models.Model)
        ):
            for obj in self._result_cache:
                obj.set_current_language(self._language)

    def _extract_model_params(self, defaults, **kwargs):
        # default implementation in Django>=1.11 doesn't allow non-field attributes,
        # so process them manually
        translated_defaults = {}
        if defaults:
            for field in self.model._parler_meta.get_all_fields():
                try:
                    translated_defaults[field] = defaults.pop(field)
                except KeyError:
                    pass

        params = super()._extract_model_params(defaults, **kwargs)
        params.update(translated_defaults)
        return params

    def language(self, language_code=None):
        """
        Set the language code to assign to objects retrieved using this QuerySet.
        """
        if language_code is None:
            language_code = appsettings.PARLER_LANGUAGES.get_default_language()

        self._language = language_code
        return self

    def translated(self, *language_codes, **translated_fields):
        """
        Only return translated objects which of the given languages.

        When no language codes are given, only the currently active language is returned.

        .. note::

            Due to Django `ORM limitations <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_,
            this method can't be combined with other filters that access the translated fields. As such, query the fields in one filter:

            .. code-block:: python

                qs.translated('en', name="Cheese Omelette")

            This will query the translated model for the ``name`` field.
        """
        relname = self.model._parler_meta.root_rel_name

        if not language_codes:
            language_codes = (get_language(),)

        filters = {}
        for field_name, val in translated_fields.items():
            if field_name.startswith("master__"):
                filters[field_name[8:]] = val  # avoid translations__master__ back and forth
            else:
                filters[f"{relname}__{field_name}"] = val

        if len(language_codes) == 1:
            filters[relname + "__language_code"] = language_codes[0]
            return self.filter(**filters)
        else:
            filters[relname + "__language_code__in"] = language_codes
            return self.filter(**filters).distinct()

    def active_translations(self, language_code=None, **translated_fields):
        """
        Only return objects which are translated, or have a fallback that should be displayed.

        Typically that's the currently active language and fallback language.
        This should be combined with ``.distinct()``.

        When ``hide_untranslated = True``, only the currently active language will be returned.
        """
        # Default:     (language, fallback) when hide_translated == False
        # Alternative: (language,)          when hide_untranslated == True
        language_codes = get_active_language_choices(language_code)
        return self.translated(*language_codes, **translated_fields)

    def select_translation(self, language_code=None, related_name=None):
        """
        This method uses ``.select_related()`` to fetch the translation model within the same query.

        For example: if the relation name is "translations" and the language "de", the translation model can
        be accessed with ``model.translations_de``. The attribute is ``None`` if no translation has been found.
        """
        if language_code is None:
            language_code = get_language()

        if related_name is None:
            related_name = self.model._parler_meta.root_rel_name

        language_code_path = f"{related_name}__language_code"
        annotation_name = get_related_translation_annotation_name(related_name, language_code)

        if annotation_name in self._related_translation_annotations:
            return self

        clone = self._clone()

        # This information will be used by the SelectTranslationIterable to ensure that the annotation attributes are set.
        clone._related_translation_annotations.add(annotation_name)

        clone._iterable_class = SelectTranslationIterable

        return clone.annotate(**{
            annotation_name: FilteredRelation(related_name, condition=Q(**{language_code_path: language_code}))
        }).select_related(annotation_name)

    def select_active_translation(self, language_code=None, related_name=None):
        """
        Uses ``.select_translation()`` to fetch both the active and the fallback language (if available) within
        the same query.
        """
        language_codes = get_active_language_choices(language_code)

        if related_name is None:
            related_name = self.model._parler_meta.root_rel_name

        queryset = self.select_translation(language_code=language_codes[0], related_name=related_name)

        if len(language_codes) == 2:
            queryset = queryset.select_translation(language_code=language_codes[1], related_name=related_name)

        return queryset


class SelectTranslationIterable(ModelIterable):
    def __iter__(self):
        for obj in super().__iter__():
            # select_related() used by select_translation() won't set anything, if no related object has been found.
            # To avoid querying the translation models again in TranslatableModelMixin._get_translated_model(),
            # we ensure that the attribute is always present.
            for annotation_name in self.queryset._related_translation_annotations:
                if not hasattr(obj, annotation_name):
                    setattr(obj, annotation_name, None)
            yield obj


class TranslatableManager(models.Manager.from_queryset(TranslatableQuerySet)):
    """
    The manager class which ensures the enhanced TranslatableQuerySet object is used.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if not isinstance(qs, TranslatableQuerySet):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__}._queryset_class does not inherit from TranslatableQuerySet"
            )
        return qs


# Export the names in django-hvad style too:
TranslationQueryset = TranslatableQuerySet
TranslationManager = TranslatableManager
