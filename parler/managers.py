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
from parler.utils.fields import get_extra_related_translation_paths


if (1, 8) <= django.VERSION < (1, 9):
    from django.db.models.query import ValuesListQuerySet, ValuesQuerySet


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
            extra_paths += get_extra_related_translation_paths(self.model, field)
        if extra_paths:
            fields = tuple(set(extra_paths)) + fields
        return super(SelectRelatedTranslationsQuerySetMixin, self).select_related(*fields)


class AutoAddSelectRelatedQuerySetMixin(object):
    """
    Mixin auto adds select related models from the list self.select_related_to_auto_add
    if it possible: QuerySet not for update and not returns values/values_list

    select_related is not compatible with values/values_list method and raise error in Django 1.8+ if it used
    so we check if select_related is applicable for the queryset

    Set related fields in your qs like:
        class YourQuerySet(AutoAddSelectRelatedQuerySetMixIn, query.QuerySet):
            select_related_fields_to_auto_add = {
                'field1': ['related_model1__field2, 'related_model2__field3, ...],
                'field2': ['related_model3__field4, 'related_model4__field5, ...]
            }
            ...

    Can be used for translated and normal model querysets to automate adding select related of any needed models to qs
    """
    select_related_fields_to_auto_add = dict()  # type: Dict[str, List[str]]

    if django.VERSION < (1, 8):
        @property
        def select_related_is_applicable(self):
            return False

    elif (1, 8) <= django.VERSION < (1, 9):
        @property
        def select_related_is_applicable(self):
            if self.model._meta.proxy:
                return False
            return not isinstance(self, ValuesListQuerySet) and not isinstance(self, ValuesQuerySet)

    elif django.VERSION >= (1, 9):
        def __init__(self, *args, **kwargs):
            super(AutoAddSelectRelatedQuerySetMixin, self).__init__(*args, **kwargs)
            self._use_values = False  # Will use _use_values as a flag if values/values_list is used

        def _values(self, *fields):
            result = super(AutoAddSelectRelatedQuerySetMixin, self)._values(*fields)
            result._use_values = True
            return result

        def _clone(self, **kwargs):
            c = super(AutoAddSelectRelatedQuerySetMixin, self)._clone(**kwargs)
            c._use_values = self._use_values
            return c

        @property
        def select_related_is_applicable(self):
            if self.model._meta.proxy:
                return False
            return not self._use_values

    def _add_select_related(self):
        """
        Adds select related fields based on select_related_fields_to_auto_add structure in format Dict[str, List[str]]
        If there are not used only/defer on queryset: query.deferred_loading = (None, False)
        we count all select_related_fields_to_auto_add are selecting and add all related fields,
        else add only subset of them as intersection with query deferred field set
        """
        existing, defer = self.query.deferred_loading

        used_fields = set(self.select_related_fields_to_auto_add.keys())
        related_fields = set()

        if defer:
            used_fields = used_fields.difference(existing)
        elif existing:
            used_fields = used_fields.intersection(existing)

        for field, related_field_list in six.iteritems(self.select_related_fields_to_auto_add):
            if field in used_fields:
                related_fields.update(related_field_list)

        if not defer and existing:
            existing.update(related_fields)

        self.query.add_select_related(related_fields)

    def _fetch_all(self):
        # Add select_related only once just before run db-query
        if self.select_related_is_applicable and not self._for_write:
            self._add_select_related()
        super(AutoAddSelectRelatedQuerySetMixin, self)._fetch_all()

    def iterator(self):
        # Add select_related only once just before run db-query
        if self.select_related_is_applicable and not self._for_write:
            self._add_select_related()
        return super(AutoAddSelectRelatedQuerySetMixin, self).iterator()


class TranslatableQuerySet(AutoAddSelectRelatedQuerySetMixin, QuerySet):
    """
    An enhancement of the QuerySet which sets the objects language before they are returned.

    When using this class in combination with *django-polymorphic*, make sure this
    class is first in the chain of inherited classes.

    When force_select_related_translations set to True it will always adds translated models with active and
    default languages by using virtual composite FKs.
    In light version QS with force select related False you can always add translated models to select_related manually.
    When you call select_related with translations rel_name e.g: 'translations' it automatically adds active and
    default translated models to select_related.
    """

    force_select_related_translations = True

    def __init__(self, *args, **kwargs):
        super(TranslatableQuerySet, self).__init__(*args, **kwargs)
        self._language = None
        if not self.force_select_related_translations:
            return
        fields_dict = self.select_related_fields_to_auto_add.copy()
        for extension in self.model._parler_meta:
            fields_dict[extension.rel_name_active] = [extension.rel_name_active]
            fields_dict[extension.rel_name_default] = [extension.rel_name_default]
        self.select_related_fields_to_auto_add = fields_dict

    def select_related(self, *fields):
        """
        Replaces main field refer to translations ('translations') with 'translations_active' and 'translations_default'
        """
        fields_to_add = set()
        fields_to_exclude = set()
        for extension in self.model._parler_meta:
            select_related_translations_fields = extension.get_select_related_translations_fields()
            fields_to_search = set(select_related_translations_fields + [extension.rel_name])
            if fields_to_search.intersection(fields):
                fields_to_exclude.add(extension.rel_name)  # Can not select related OneToMany field
                fields_to_add.update(select_related_translations_fields)
        fields = set(fields).union(fields_to_add).difference(fields_to_exclude)
        return super(TranslatableQuerySet, self).select_related(*tuple(fields))

    def only(self, *fields):
        """
        Replaces translated fields with 'translations_active' and 'translations_default'
        pretending they are in original model so we can use .only
        for translated fields as usual: .objects.only('some_translated_field')
        """
        fields_to_add = set()
        fields_to_exclude = set()
        for extension in self.model._parler_meta:
            select_related_translations_fields = extension.get_select_related_translations_fields()
            # List fields to replace with select_related_translations_fields
            fields_to_search = set(extension.get_translated_fields() + [extension.rel_name])
            if fields_to_search.intersection(fields):
                fields_to_exclude.update(fields_to_search)
                fields_to_add.update(select_related_translations_fields)
        fields = set(fields).union(fields_to_add).difference(fields_to_exclude)
        return super(TranslatableQuerySet, self).only(*tuple(fields))

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

    def _fetch_all(self):
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


class LightTranslatableQuerySet(TranslatableQuerySet):
    force_select_related_translations = False


class LightTranslatableManager(TranslatableManager):
    """
    Translatable manager does not auto add select related translation models
    """
    queryset_class = LightTranslatableQuerySet


class DeepTranslatableQuerySet(SelectRelatedTranslationsQuerySetMixin, TranslatableQuerySet):
    pass


class DeepTranslatableManager(TranslatableManager):
    """
    Translatable manager does auto add select related translation models (for active and default languages)
    for current model and all translatable models used in select_related method call
    """
    queryset_class = DeepTranslatableQuerySet


class AutoAddTranslationsQuerySet(SelectRelatedTranslationsQuerySetMixin, models.query.QuerySet):
    pass


class AutoAddTranslationsManager(models.Manager.from_queryset(AutoAddTranslationsQuerySet)):
    """
    Manager does auto add select related translation models (for active and default languages)
    for all translatable models used in select_related method call
    """
    queryset_class = AutoAddTranslationsQuerySet


# Export the names in django-hvad style too:
TranslationQueryset = TranslatableQuerySet
TranslationManager = TranslatableManager
