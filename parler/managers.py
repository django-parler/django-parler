"""
Custom generic managers
"""
import django
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import get_language
from django.utils import six
from parler import appsettings
from parler.utils import get_active_language_choices
from parler.utils.fields import get_extra_related_translalation_paths


class SelectRelatedTranslationsQuerySetMixin(object):
    """
    Mixin to add to the QuerySets which joins with translatable models by select_related.
    Automatically adds active and default translation models to query join tables
    for all occurrences of models with translations in select_related paths.
    Use it in your normal models which join with translatable models.

    TODO: add/remove extra_paths to deferred_loading if it used
    """
    def select_related(self, *fields):
        extra_paths = []
        for field in fields:
            extra_paths += get_extra_related_translalation_paths(self.model, field)
        if extra_paths:
            fields = tuple(set(extra_paths)) + fields
        return super(SelectRelatedTranslationsQuerySetMixin, self).select_related(*fields)


class TranslatableQuerySet(QuerySet):
    """
    An enhancement of the QuerySet which sets the objects language before they are returned.

    When using this class in combination with *django-polymorphic*, make sure this
    class is first in the chain of inherited classes.

    When force_select_related_translations set to True in your classes it will always
    adds active and default languages to select_related. It could break values_list method in django 1.9+
    You can always add translated models to select_related manually. When you call it with rel_name e.g: 'translations'
    it automatically adds active and default virtual composite FKs.
    """

    force_select_related_translations = False

    def __init__(self, *args, **kwargs):
        super(TranslatableQuerySet, self).__init__(*args, **kwargs)
        self._language = None

    def select_related(self, *fields):
        fields_to_add = []
        fields_to_exclude = []
        for extension in self.model._parler_meta:
            if extension.rel_name in fields:
                fields_to_exclude.append(extension.rel_name)  # Can not select related OneToMany field
                fields_to_add.append(extension.rel_name_active)
                fields_to_add.append(extension.rel_name_default)
            if extension.rel_name_active in fields:
                fields_to_add.append(extension.rel_name_default)
            if extension.rel_name_default in fields:
                fields_to_add.append(extension.rel_name_active)
        fields = [field for field in fields if field not in fields_to_exclude] + fields_to_add
        return super(TranslatableQuerySet, self).select_related(*tuple(set(fields)))

    def _clone(self, klass=None, setup=False, **kw):
        if django.VERSION < (1, 9):
            kw['klass'] = klass
            kw['setup'] = setup
        c = super(TranslatableQuerySet, self)._clone(**kw)
        c._language = self._language
        return c

    def create(self, **kwargs):
        # Pass language setting to the object, as people start assuming things
        # like .language('xx').create(..) which is a nice API after all.
        if self._language:
            kwargs['_current_language'] = self._language
        return super(TranslatableQuerySet, self).create(**kwargs)

    def _add_active_default_select_related(self):
        existing, defer = self.query.deferred_loading
        related_to_add = set()
        for extension in self.model._parler_meta:
            if extension.rel_name:
                related_to_add.add(extension.rel_name_active)
                related_to_add.add(extension.rel_name_default)
        if defer:
            related_to_add = related_to_add.difference(existing)
        elif existing:
            related_to_add = related_to_add.intersection(existing)
        self.query.add_select_related(related_to_add)

    @property
    def select_related_not_applicable(self):
        # type: () -> Union[bool, None]
        """
        Returns is select_related not applicable for current qs.
        Currently determine only for django ver 1.8, for others returns None
        """
        result = None
        if self.model._meta.proxy:
            return True

        if (1, 7) < django.VERSION < (1, 9):
            ValuesListQuerySet = getattr(django.db.models.query, 'ValuesListQuerySet')
            result = isinstance(self, ValuesListQuerySet)

        return result

    def _fetch_all(self):
        # For django ver > 1.8 when values_list method is used
        #  _iterable_class (FlatValuesListIterable, ValuesListIterable) is known only in iteration stage not here yet
        # TODO: figure out how to determine non qs methods or
        #       place _add_active_default_select_related in some other place
        if self.force_select_related_translations and not self.select_related_not_applicable:
            self._add_active_default_select_related()

        # Make sure the current language is assigned when Django fetches the data.
        # This low-level method is overwritten as that works better across Django versions.
        # Alternatives include:
        # - overwriting iterator() for Django <= 1.10
        # - hacking _iterable_class, which breaks django-polymorphic
        super(TranslatableQuerySet, self)._fetch_all()
        if self._language is not None and self._result_cache and isinstance(self._result_cache[0], models.Model):
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

        lookup, params = super(TranslatableQuerySet, self)._extract_model_params(defaults, **kwargs)
        params.update(translated_defaults)

        if (1, 7) <= django.VERSION < (1, 8):
            if self._language:
                params['_current_language'] = self._language

        return lookup, params

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
        for field_name, val in six.iteritems(translated_fields):
            if field_name.startswith('master__'):
                filters[field_name[8:]] = val  # avoid translations__master__ back and forth
            else:
                filters["{0}__{1}".format(relname, field_name)] = val

        if len(language_codes) == 1:
            filters[relname + '__language_code'] = language_codes[0]
            return self.filter(**filters)
        else:
            filters[relname + '__language_code__in'] = language_codes
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


class TranslatableManager(models.Manager):
    """
    The manager class which ensures the enhanced TranslatableQuerySet object is used.
    """
    queryset_class = TranslatableQuerySet

    def get_queryset(self):
        if not issubclass(self.queryset_class, TranslatableQuerySet):
            raise ImproperlyConfigured("{0}.queryset_class does not inherit from TranslatableQuerySet".format(self.__class__.__name__))
        return self.queryset_class(self.model, using=self._db)

    # Leave for Django 1.6/1.7, so backwards compatibility can be fixed.
    # It will be removed in Django 1.8, so remove it here too to avoid false promises.
    if django.VERSION < (1, 8):
        get_query_set = get_queryset

    # NOTE: Fetching the queryset is done by calling self.all() here on purpose.
    # By using .all(), the proper get_query_set()/get_queryset() will be used for each Django version.

    def language(self, language_code=None):
        """
        Set the language code to assign to objects retrieved using this Manager.
        """
        return self.all().language(language_code)

    def translated(self, *language_codes, **translated_fields):
        """
        Only return objects which are translated in the given languages.

        NOTE: due to Django `ORM limitations <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_,
        this method can't be combined with other filters that access the translated fields. As such, query the fields in one filter:

        .. code-block:: python

            qs.translated('en', name="Cheese Omelette")

        This will query the translated model for the ``name`` field.
        """
        return self.all().translated(*language_codes, **translated_fields)

    def active_translations(self, language_code=None, **translated_fields):
        """
        Only return objects which are translated, or have a fallback that should be displayed.

        Typically that's the currently active language and fallback language.
        This should be combined with ``.distinct()``.

        When ``hide_untranslated = True``, only the currently active language will be returned.
        """
        return self.all().active_translations(language_code, **translated_fields)


class TranslatableAutoSelectRelatedQuerySet(TranslatableQuerySet):
    force_select_related_translations = True


class TranslatableAutoSelectRelatedManager(TranslatableManager):
    queryset_class = TranslatableAutoSelectRelatedQuerySet


# Export the names in django-hvad style too:
TranslationQueryset = TranslatableQuerySet
TranslationManager = TranslatableManager
