"""
The models and fields for translation support.

The default is to use the :class:`TranslatedFields` class in the model, like:

.. code-block:: python

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFields


    class MyModel(TranslatableModel):
        translations = TranslatedFields(
            title = models.CharField(_("Title"), max_length=200)
        )

        class Meta:
            verbose_name = _("MyModel")

        def __unicode__(self):
            return self.title


It's also possible to create the translated fields model manually:

.. code-block:: python

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFieldsModel
    from parler.fields import TranslatedField


    class MyModel(TranslatableModel):
        title = TranslatedField()  # Optional, explicitly mention the field

        class Meta:
            verbose_name = _("MyModel")

        def __unicode__(self):
            return self.title


    class MyModelTranslation(TranslatedFieldsModel):
        master = models.ForeignKey(MyModel, related_name='translations', null=True)
        title = models.CharField(_("Title"), max_length=200)

        class Meta:
            verbose_name = _("MyModel translation")

This has the same effect, but also allows to to override
the :func:`~django.db.models.Model.save` method, or add new methods yourself.

The translated model is compatible with django-hvad, making the transition between both projects relatively easy.
The manager and queryset objects of django-parler can work together with django-mptt and django-polymorphic.
"""
from __future__ import unicode_literals
from collections import defaultdict
import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError, FieldError, ObjectDoesNotExist
from django.db import models, router
from django.db.models.base import ModelBase
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor
from django.utils.functional import lazy
from django.utils.translation import get_language, ugettext, ugettext_lazy as _
from django.utils import six
from parler import signals
from parler.cache import MISSING, _cache_translation, _cache_translation_needs_fallback, _delete_cached_translation, get_cached_translation, _delete_cached_translations, get_cached_translated_field
from parler.fields import TranslatedField, LanguageCodeDescriptor, TranslatedFieldDescriptor
from parler.managers import TranslatableManager
from parler.utils import compat
from parler.utils.i18n import normalize_language_code, get_language_settings, get_language_title
import sys

try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict


__all__ = (
    'TranslatableModel',
    'TranslatedFields',
    'TranslatedFieldsModel',
    'TranslatedFieldsModelBase',
    'TranslationDoesNotExist',
    #'create_translations_model',
)


class TranslationDoesNotExist(AttributeError, ObjectDoesNotExist):
    """
    A tagging interface to detect missing translations.
    The exception inherits from :class:`~exceptions.AttributeError` to reflect what is actually happening.
    Therefore it also causes the templates to handle the missing attributes silently, which is very useful in the admin for example.
    The exception also inherits from :class:`~django.core.exceptions.ObjectDoesNotExist`,
    so any code that checks for this can deal with missing translations out of the box.

    This class is also used in the ``DoesNotExist`` object on the translated model, which inherits from:

    * this class
    * the ``sharedmodel.DoesNotExist`` class
    * the original ``translatedmodel.DoesNotExist`` class.

    This makes sure that the regular code flow is decently handled by existing exception handlers.
    """
    pass


_lazy_verbose_name = lazy(lambda x: ugettext("{0} Translation").format(x._meta.verbose_name), six.text_type)


def create_translations_model(shared_model, related_name, meta, **fields):
    """
    Dynamically create the translations model.
    Create the translations model for the shared model 'model'.

    :param related_name: The related name for the reverse FK from the translations model.
    :param meta: A (optional) dictionary of attributes for the translations model's inner Meta class.
    :param fields: A dictionary of fields to put on the translations model.

    Two fields are enforced on the translations model:

        language_code: A 15 char, db indexed field.
        master: A ForeignKey back to the shared model.

    Those two fields are unique together.
    """
    if not meta:
        meta = {}

    if shared_model._meta.abstract:
        # This can't be done, because `master = ForeignKey(shared_model)` would fail.
        raise TypeError("Can't create TranslatedFieldsModel for abstract class {0}".format(shared_model.__name__))

    # Define inner Meta class
    meta['app_label'] = shared_model._meta.app_label
    meta['db_tablespace'] = shared_model._meta.db_tablespace
    meta['managed'] = shared_model._meta.managed
    meta['unique_together'] = list(meta.get('unique_together', [])) + [('language_code', 'master')]
    meta.setdefault('db_table', '{0}_translation'.format(shared_model._meta.db_table))
    meta.setdefault('verbose_name', _lazy_verbose_name(shared_model))

    # Avoid creating permissions for the translated model, these are not used at all.
    # This also avoids creating lengthy permission names above 50 chars.
    if django.VERSION >= (1,7):
        meta.setdefault('default_permissions', ())

    # Define attributes for translation table
    name = str('{0}Translation'.format(shared_model.__name__))  # makes it bytes, for type()

    attrs = {}
    attrs.update(fields)
    attrs['Meta'] = type(str('Meta'), (object,), meta)
    attrs['__module__'] = shared_model.__module__
    attrs['objects'] = models.Manager()
    attrs['master'] = models.ForeignKey(shared_model, related_name=related_name, editable=False, null=True)

    # Create and return the new model
    translations_model = TranslatedFieldsModelBase(name, (TranslatedFieldsModel,), attrs)

    # Register it as a global in the shared model's module.
    # This is needed so that Translation model instances, and objects which refer to them, can be properly pickled and unpickled.
    # The Django session and caching frameworks, in particular, depend on this behaviour.
    mod = sys.modules[shared_model.__module__]
    setattr(mod, name, translations_model)

    return translations_model


class TranslatedFields(object):
    """
    Wrapper class to define translated fields on a model.

    The field name becomes the related name of the :class:`TranslatedFieldsModel` subclass.

    Example:

    .. code-block:: python

        from django.db import models
        from parler.models import TranslatableModel, TranslatedFields

        class MyModel(TranslatableModel):
            translations = TranslatedFields(
                title = models.CharField("Title", max_length=200)
            )

    When the class is initialized, the attribute will point
    to a :class:`~django.db.models.fields.related.ForeignRelatedObjectsDescriptor` object.
    Hence, accessing ``MyModel.translations.related.model`` returns the original model
    via the :class:`django.db.models.related.RelatedObject` class.

    ..
       To fetch the attribute, you can also query the Parler metadata:
       MyModel._parler_meta.get_model_by_related_name('translations')
    """
    def __init__(self, meta=None, **fields):
        self.fields = fields
        self.meta = meta
        self.name = None

    def contribute_to_class(self, cls, name):
        # Called from django.db.models.base.ModelBase.__new__
        self.name = name
        create_translations_model(cls, name, self.meta, **self.fields)


class TranslatableModel(models.Model):
    """
    Base model class to handle translations.

    All translatable fields will appear on this model, proxying the calls to the :class:`TranslatedFieldsModel`.
    """
    class Meta:
        abstract = True

    #: Access to the metadata of the translatable model
    _parler_meta = None

    #: Access to the language code
    language_code = LanguageCodeDescriptor()

    # change the default manager to the translation manager
    objects = TranslatableManager()

    def __init__(self, *args, **kwargs):
        # Still allow to pass the translated fields (e.g. title=...) to this function.
        translated_kwargs = {}
        current_language = None
        if kwargs:
            current_language = kwargs.pop('_current_language', None)
            for field in self._parler_meta.get_all_fields():
                try:
                    translated_kwargs[field] = kwargs.pop(field)
                except KeyError:
                    pass

        # Have the attributes available, but they can't be ready yet;
        # self._state.adding is always True at this point,
        # the QuerySet.iterator() code changes it after construction.
        self._translations_cache = None
        self._current_language = None

        # Run original Django model __init__
        super(TranslatableModel, self).__init__(*args, **kwargs)

        # Assign translated args manually.
        self._translations_cache = defaultdict(dict)
        self._current_language = normalize_language_code(current_language or get_language())  # What you used to fetch the object is what you get.

        if translated_kwargs:
            self._set_translated_fields(self._current_language, **translated_kwargs)


    def _set_translated_fields(self, language_code=None, **fields):
        """
        Assign fields to the translated models.
        """
        objects = []  # no generator, make sure objects are all filled first
        for parler_meta, model_fields in self._parler_meta._split_fields(**fields):
            translation = self._get_translated_model(language_code=language_code, auto_create=True, meta=parler_meta)
            for field, value in six.iteritems(model_fields):
                setattr(translation, field, value)

            objects.append(translation)
        return objects


    def create_translation(self, language_code, **fields):
        """
        Add a translation to the model.

        The :func:`save_translations` function is called afterwards.

        The object will be saved immediately, similar to
        calling :func:`~django.db.models.manager.Manager.create`
        or :func:`~django.db.models.fields.related.RelatedManager.create` on related fields.
        """
        meta = self._parler_meta
        if self._translations_cache[meta.root_model].get(language_code, None):  # MISSING evaluates to False too
            raise ValueError("Translation already exists: {0}".format(language_code))

        # Save all fields in the proper translated model.
        for translation in self._set_translated_fields(language_code, **fields):
            self.save_translation(translation)


    def get_current_language(self):
        """
        Get the current language.
        """
        # not a property, so won't conflict with model fields.
        return self._current_language


    def set_current_language(self, language_code, initialize=False):
        """
        Switch the currently activate language of the object.
        """
        self._current_language = normalize_language_code(language_code or get_language())

        # Ensure the translation is present for __get__ queries.
        if initialize:
            self._get_translated_model(use_fallback=False, auto_create=True)


    def get_fallback_language(self):
        """
        Return the fallback language code,
        which is used in case there is no translation for the currently active language.
        """
        lang_dict = get_language_settings(self._current_language)
        return lang_dict['fallback'] if lang_dict['fallback'] != self._current_language else None


    def has_translation(self, language_code=None, related_name=None):
        """
        Return whether a translation for the given language exists.
        Defaults to the current language code.

        .. versionadded 1.2 Added the ``related_name`` parameter.
        """
        if language_code is None:
            language_code = self._current_language

        meta = self._parler_meta._get_extension_by_related_name(related_name)

        try:
            # Check the local cache directly, and the answer is known.
            # NOTE this may also return newly auto created translations which are not saved yet.
            return self._translations_cache[meta.model][language_code] is not MISSING
        except KeyError:
            # Try to fetch from the cache first.
            # If the cache returns the fallback, it means the original does not exist.
            object = get_cached_translation(self, language_code, related_name=related_name, use_fallback=True)
            if object is not None:
                return object.language_code == language_code

            try:
                # Fetch from DB, fill the cache.
                self._get_translated_model(language_code, use_fallback=False, auto_create=False, meta=meta)
            except meta.model.DoesNotExist:
                return False
            else:
                return True


    def get_available_languages(self, related_name=None, include_unsaved=False):
        """
        Return the language codes of all translated variations.

        .. versionadded 1.2 Added the ``include_unsaved`` and ``related_name`` parameters.
        """
        meta = self._parler_meta._get_extension_by_related_name(related_name)

        prefetch = self._get_prefetched_translations(meta=meta)
        if prefetch is not None:
            db_languages = sorted(obj.language_code for obj in prefetch)
        else:
            qs = self._get_translated_queryset(meta=meta)
            db_languages = qs.values_list('language_code', flat=True).order_by('language_code')

        if include_unsaved:
            local_languages = (k for k,v in six.iteritems(self._translations_cache[meta.model]) if v is not MISSING)
            return list(set(db_languages) | set(local_languages))
        else:
            return db_languages


    def get_translation(self, language_code, related_name=None):
        """
        Fetch the translated model
        """
        meta = self._parler_meta._get_extension_by_related_name(related_name)
        return self._get_translated_model(language_code, meta=meta)


    def _get_translated_model(self, language_code=None, use_fallback=False, auto_create=False, meta=None):
        """
        Fetch the translated fields model.
        """
        if self._parler_meta is None:
            raise ImproperlyConfigured("No translation is assigned to the current model!")
        if self._translations_cache is None:
            raise RuntimeError("Accessing translated fields before super.__init__() is not possible.")

        if not language_code:
            language_code = self._current_language
        if meta is None:
            meta = self._parler_meta.root  # work on base model by default

        local_cache = self._translations_cache[meta.model]

        # 1. fetch the object from the local cache
        try:
            object = local_cache[language_code]

            # If cached object indicates the language doesn't exist, need to query the fallback.
            if object is not MISSING:
                return object
        except KeyError:
            # 2. No cache, need to query
            # Check that this object already exists, would be pointless otherwise to check for a translation.
            if not self._state.adding and self.pk is not None:
                prefetch = self._get_prefetched_translations(meta=meta)
                if prefetch is not None:
                    # 2.1, use prefetched data
                    # If the object is not found in the prefetched data (which contains all translations),
                    # it's pointless to check for memcached (2.2) or perform a single query (2.3)
                    for object in prefetch:
                        if object.language_code == language_code:
                            local_cache[language_code] = object
                            _cache_translation(object)  # Store in memcached
                            return object
                else:
                    # 2.2, fetch from memcached
                    object = get_cached_translation(self, language_code, related_name=meta.rel_name, use_fallback=use_fallback)
                    if object is not None:
                        # Track in local cache
                        if object.language_code != language_code:
                            local_cache[language_code] = MISSING  # Set fallback marker
                        local_cache[object.language_code] = object
                        return object
                    elif local_cache.get(language_code, None) is MISSING:
                        # If get_cached_translation() explicitly set the "does not exist" marker,
                        # there is no need to try a database query.
                        pass
                    else:
                        # 2.3, fetch from database
                        try:
                            object = self._get_translated_queryset(meta).get(language_code=language_code)
                        except meta.model.DoesNotExist:
                            pass
                        else:
                            local_cache[language_code] = object
                            _cache_translation(object)  # Store in memcached
                            return object

        # Not in cache, or default.
        # Not fetched from DB

        # 3. Auto create?
        if auto_create:
            # Auto create policy first (e.g. a __set__ call)
            object = meta.model(
                language_code=language_code,
                master=self  # ID might be None at this point
            )
            local_cache[language_code] = object
            # Not stored in memcached here yet, first fill + save it.
            return object

        # 4. Fallback?
        fallback_msg = None
        lang_dict = get_language_settings(language_code)

        if language_code not in local_cache:
            # Explicitly set a marker for the fact that this translation uses the fallback instead.
            # Avoid making that query again.
            local_cache[language_code] = MISSING  # None value is the marker.
            if not self._state.adding or self.pk is not None:
                _cache_translation_needs_fallback(self, language_code, related_name=meta.rel_name)

        if lang_dict['fallback'] != language_code and use_fallback:
            # Jump to fallback language, return directly.
            # Don't cache under this language_code
            try:
                return self._get_translated_model(lang_dict['fallback'], use_fallback=False, auto_create=auto_create, meta=meta)
            except meta.model.DoesNotExist:
                fallback_msg = " (tried fallback {0})".format(lang_dict['fallback'])

        # None of the above, bail out!
        raise meta.model.DoesNotExist(
            "{0} does not have a translation for the current language!\n"
            "{0} ID #{1}, language={2}{3}".format(self._meta.verbose_name, self.pk, language_code, fallback_msg or ''
        ))


    def _get_any_translated_model(self, meta=None):
        """
        Return any available translation.
        Returns None if there are no translations at all.
        """
        if meta is None:
            meta = self._parler_meta.root

        tr_model = meta.model
        local_cache = self._translations_cache[tr_model]
        if local_cache:
            # There is already a language available in the case. No need for queries.
            # Give consistent answers if they exist.
            try:
                return local_cache.get(self._current_language, None) \
                    or local_cache.get(self.get_fallback_language(), None) \
                    or next(t for t in six.itervalues(local_cache) if t is not MISSING)  # Skip fallback markers.
            except StopIteration:
                pass

        try:
            # Use prefetch if available, otherwise perform separate query.
            prefetch = self._get_prefetched_translations(meta=meta)
            if prefetch is not None:
                translation = prefetch[0]  # Already a list
            else:
                translation = self._get_translated_queryset(meta=meta)[0]
        except IndexError:
            return None
        else:
            local_cache[translation.language_code] = translation
            _cache_translation(translation)
            return translation


    def _get_translated_queryset(self, meta=None):
        """
        Return the queryset that points to the translated model.
        If there is a prefetch, it can be read from this queryset.
        """
        # Get via self.TRANSLATIONS_FIELD.get(..) so it also uses the prefetch/select_related cache.
        if meta is None:
            meta = self._parler_meta.root

        accessor = getattr(self, meta.rel_name)
        if django.VERSION >= (1,6):
            # Call latest version
            return accessor.get_queryset()
        else:
            # Must call RelatedManager.get_query_set() and avoid calling a custom get_queryset()
            # method for packages with Django 1.6/1.7 compatibility.
            return accessor.get_query_set()


    def _get_prefetched_translations(self, meta=None):
        """
        Return the queryset with prefetch results.
        """
        if meta is None:
            meta = self._parler_meta.root

        related_name = meta.rel_name
        try:
            # Read the list directly, avoid QuerySet construction.
            # Accessing self._get_translated_queryset(parler_meta)._prefetch_done is more expensive.
            return self._prefetched_objects_cache[related_name]
        except (AttributeError, KeyError):
            return None

    def save(self, *args, **kwargs):
        super(TranslatableModel, self).save(*args, **kwargs)
        self.save_translations(*args, **kwargs)


    def delete(self, using=None):
        _delete_cached_translations(self)
        super(TranslatableModel, self).delete(using)


    def validate_unique(self, exclude=None):
        """
        Also validate the unique_together of the translated model.
        """
        # This is called from ModelForm._post_clean() or Model.full_clean()
        errors = {}
        try:
            super(TranslatableModel, self).validate_unique(exclude=exclude)
        except ValidationError as e:
            errors = e.message_dict  # Django 1.5 + 1.6 compatible

        for local_cache in six.itervalues(self._translations_cache):
            for translation in six.itervalues(local_cache):
                if translation is MISSING:  # Skip fallback markers
                    continue

                try:
                    translation.validate_unique(exclude=exclude)
                except ValidationError as e:
                    errors.update(e.message_dict)

        if errors:
            raise ValidationError(errors)


    def save_translations(self, *args, **kwargs):
        """
        The method to save all translations.
        This can be overwritten to implement any custom additions.
        This method calls :func:`save_translation` for every fetched language.

        :param args: Any custom arguments to pass to :func:`save`.
        :param kwargs: Any custom arguments to pass to :func:`save`.
        """
        # Copy cache, new objects (e.g. fallbacks) might be fetched if users override save_translation()
        # Not looping over the cache, but using _parler_meta so the translations are processed in the order of inheritance.
        local_caches = self._translations_cache.copy()
        for meta in self._parler_meta:
            local_cache = local_caches[meta.model]
            translations = list(local_cache.values())

            # Save all translated objects which were fetched.
            # This also supports switching languages several times, and save everything in the end.
            for translation in translations:
                if translation is MISSING:  # Skip fallback markers
                    continue

                self.save_translation(translation, *args, **kwargs)


    def save_translation(self, translation, *args, **kwargs):
        """
        Save the translation when it's modified, or unsaved.

        .. note::

           When a derived model provides additional translated fields,
           this method receives both the original and extended translation.
           To distinguish between both objects, check for ``translation.related_name``.

        :param translation: The translation
        :type translation: TranslatedFieldsModel
        :param args: Any custom arguments to pass to :func:`save`.
        :param kwargs: Any custom arguments to pass to :func:`save`.
        """
        if self.pk is None or self._state.adding:
            raise RuntimeError("Can't save translations when the master object is not yet saved.")

        # Translation models without any fields are also supported.
        # This is useful for parent objects that have inlines;
        # the parent object defines how many translations there are.
        if translation.is_modified or (translation.is_empty and not translation.pk):
            if not translation.master_id:  # Might not exist during first construction
                translation._state.db = self._state.db
                translation.master = self
            translation.save(*args, **kwargs)


    def safe_translation_getter(self, field, default=None, language_code=None, any_language=False):
        """
        Fetch a translated property, and return a default value
        when both the translation and fallback language are missing.

        When ``any_language=True`` is used, the function also looks
        into other languages to find a suitable value. This feature can be useful
        for "title" attributes for example, to make sure there is at least something being displayed.
        Also consider using ``field = TranslatedField(any_language=True)`` in the model itself,
        to make this behavior the default for the given field.
        """
        meta = self._parler_meta._get_extension_by_field(field)

        # Extra feature: query a single field from a other translation.
        if language_code and language_code != self._current_language:
            try:
                tr_model = self._get_translated_model(language_code, meta=meta, use_fallback=True)
                return getattr(tr_model, field)
            except TranslationDoesNotExist:
                pass
        else:
            # By default, query via descriptor (TranslatedFieldDescriptor)
            # which also attempts the fallback language if configured to do so.
            try:
                return getattr(self, field)
            except TranslationDoesNotExist:
                pass

        if any_language:
            translation = self._get_any_translated_model(meta=meta)
            if translation is not None:
                return getattr(translation, field, default)

        return default


class TranslatedFieldsModelBase(ModelBase):
    """
    .. versionadded 1.2

    Meta-class for the translated fields model.

    It performs the following steps:

    * It validates the 'master' field, in case it's added manually.
    * It tells the original model to use this model for translations.
    * It adds the proxy attributes to the shared model.
    """
    def __new__(mcs, name, bases, attrs):

        # Workaround compatibility issue with six.with_metaclass() and custom Django model metaclasses:
        if not attrs and name == 'NewBase':
            if django.VERSION < (1,5):
                # Let Django fully ignore the class which is inserted in between.
                # Django 1.5 fixed this, see https://code.djangoproject.com/ticket/19688
                attrs['__module__'] = 'django.utils.six'
                attrs['Meta'] = type(str('Meta'), (), {'abstract': True})
            return super(TranslatedFieldsModelBase, mcs).__new__(mcs, name, bases, attrs)

        new_class = super(TranslatedFieldsModelBase, mcs).__new__(mcs, name, bases, attrs)
        if bases[0] == models.Model:
            return new_class

        # No action in abstract models.
        if new_class._meta.abstract or new_class._meta.proxy:
            return new_class

        # Validate a manually configured class.
        shared_model = _validate_master(new_class)

        # Add wrappers for all translated fields to the shared models.
        new_class.contribute_translations(shared_model)

        return new_class


def _validate_master(new_class):
    """
    Check whether the 'master' field on a TranslatedFieldsModel is correctly configured.
    """
    if not new_class.master or not isinstance(new_class.master, ReverseSingleRelatedObjectDescriptor):
        raise ImproperlyConfigured("{0}.master should be a ForeignKey to the shared table.".format(new_class.__name__))

    rel = new_class.master.field.rel
    shared_model = rel.to

    if not issubclass(shared_model, models.Model):
        # Not supporting models.ForeignKey("tablename") yet. Can't use get_model() as the models are still being constructed.
        raise ImproperlyConfigured("{0}.master should point to a model class, can't use named field here.".format(new_class.__name__))

    meta = shared_model._parler_meta
    if meta is not None:
        if meta._has_translations_model(new_class):
            raise ImproperlyConfigured("The model '{0}' already has an associated translation table!".format(shared_model.__name__))
        if meta._has_translations_field(rel.related_name):
            raise ImproperlyConfigured("The model '{0}' already has an associated translation field named '{1}'!".format(shared_model.__name__, rel.related_name))

    return shared_model


class TranslatedFieldsModel(compat.with_metaclass(TranslatedFieldsModelBase, models.Model)):
    """
    Base class for the model that holds the translated fields.
    """
    language_code = compat.HideChoicesCharField(_("Language"), choices=settings.LANGUAGES, max_length=15, db_index=True)

    #: The mandatory Foreign key field to the shared model.
    master = None   # FK to shared model.


    class Meta:
        abstract = True
        if django.VERSION >= (1,7):
            default_permissions = ()

    def __init__(self, *args, **kwargs):
        signals.pre_translation_init.send(sender=self.__class__, args=args, kwargs=kwargs)
        super(TranslatedFieldsModel, self).__init__(*args, **kwargs)
        self._original_values = self._get_field_values()

        signals.post_translation_init.send(sender=self.__class__, args=args, kwargs=kwargs)

    @property
    def is_modified(self):
        """
        Tell whether the object content is modified since fetching it.
        """
        return self._original_values != self._get_field_values()

    @property
    def is_empty(self):
        """
        True when there are no translated fields.
        """
        return len(self.get_translated_fields()) == 0

    @property
    def shared_model(self):
        """
        Returns the shared model this model is linked to.
        """
        return self.__class__.master.field.rel.to

    @property
    def related_name(self):
        """
        Returns the related name that this model is known at in the shared model.
        """
        return self.__class__.master.field.rel.related_name

    def save_base(self, raw=False, using=None, **kwargs):
        # Send the pre_save signal
        using = using or router.db_for_write(self.__class__, instance=self)
        record_exists = self.pk is not None  # Ignoring force_insert/force_update for now.
        if not self._meta.auto_created:
            signals.pre_translation_save.send(
                sender=self.shared_model, instance=self,
                raw=raw, using=using
            )

        # Perform save
        super(TranslatedFieldsModel, self).save_base(raw=raw, using=using, **kwargs)
        self._original_values = self._get_field_values()
        _cache_translation(self)

        # Send the post_save signal
        if not self._meta.auto_created:
            signals.post_translation_save.send(
                sender=self.shared_model, instance=self, created=(not record_exists),
                raw=raw, using=using
            )

    def delete(self, using=None):
        # Send pre-delete signal
        using = using or router.db_for_write(self.__class__, instance=self)
        if not self._meta.auto_created:
            signals.pre_translation_delete.send(sender=self.shared_model, instance=self, using=using)

        super(TranslatedFieldsModel, self).delete(using=using)
        _delete_cached_translation(self)

        # Send post-delete signal
        if not self._meta.auto_created:
            signals.post_translation_delete.send(sender=self.shared_model, instance=self, using=using)

    def _get_field_values(self):
        # Return all field values in a consistent (sorted) manner.
        return [getattr(self, field.get_attname()) for field, _ in self._meta.get_fields_with_model()]

    @classmethod
    def get_translated_fields(cls):
        # Not using get `get_all_field_names()` because that also invokes a model scan.
        return [f.name for f, _ in cls._meta.get_fields_with_model() if f.name not in ('language_code', 'master', 'id')]

    @classmethod
    def contribute_translations(cls, shared_model):
        """
        Add the proxy attributes to the shared model.
        """
        # Instance at previous inheritance level, if set.
        base = shared_model._parler_meta

        if base is not None and base[-1].shared_model is shared_model:
            # If a second translations model is added, register it in the same object level.
            base.add_meta(ParlerMeta(
                shared_model=shared_model,
                translations_model=cls,
                related_name=cls.master.field.rel.related_name
            ))
        else:
            # Place a new _parler_meta at the current inheritance level.
            # It links to the previous base.
            shared_model._parler_meta = ParlerOptions(
                base,
                shared_model=shared_model,
                translations_model=cls,
                related_name=cls.master.field.rel.related_name
            )

        # Assign the proxy fields
        for name in cls.get_translated_fields():
            try:
                # Check if an attribute already exists.
                # Note that the descriptor even proxies this request, so it should return our field.
                #
                # A model field might not be added yet, as this all happens in the contribute_to_class() loop.
                # Hence, only checking attributes here. The real fields are checked for in the _prepare() code.
                shared_field = getattr(shared_model, name)
            except AttributeError:
                # Add the proxy field for the shared field.
                TranslatedField().contribute_to_class(shared_model, name)
            else:
                # Currently not allowing to replace existing model fields with translatable fields.
                # That would be a nice feature addition however.
                if not isinstance(shared_field, (models.Field, TranslatedFieldDescriptor)):
                    raise TypeError("The model '{0}' already has a field named '{1}'".format(shared_model.__name__, name))

                # When the descriptor was placed on an abstract model,
                # it doesn't point to the real model that holds the translations_model
                # "Upgrade" the descriptor on the class
                if shared_field.field.model is not shared_model:
                    TranslatedField(any_language=shared_field.field.any_language).contribute_to_class(shared_model, name)


        # Make sure the DoesNotExist error can be detected als shared_model.DoesNotExist too,
        # and by inheriting from AttributeError it makes sure (admin) templates can handle the missing attribute.
        cls.DoesNotExist = type(str('DoesNotExist'), (TranslationDoesNotExist, shared_model.DoesNotExist, cls.DoesNotExist,), {})

    def __unicode__(self):
        # use format to avoid weird error in django 1.4
        # TypeError: coercing to Unicode: need string or buffer, __proxy__ found
        return "{0}".format(get_language_title(self.language_code))

    def __repr__(self):
        return "<{0}: #{1}, {2}, master: #{3}>".format(
            self.__class__.__name__, self.pk, self.language_code, self.master_id
        )


class ParlerMeta(object):
    """
    Meta data for a single inheritance level.
    """
    def __init__(self, shared_model, translations_model, related_name):
        # Store meta information of *this* level
        self.shared_model = shared_model
        self.model = translations_model
        self.rel_name = related_name

    def get_translated_fields(self):
        """
        Return the translated fields of this model.
        """
        # TODO: should be named get_fields() ?
        # root_model always points to the real model for extensions
        return self.model.get_translated_fields()

    def __repr__(self):
        return "<ParlerMeta: {0}.{1} to {2}>".format(
            self.shared_model.__name__,
            self.rel_name,
            self.model.__name__
        )


class ParlerOptions(object):
    """
    Meta data for the translatable models.
    """
    def __init__(self, base, shared_model, translations_model, related_name):
        if translations_model is None is not issubclass(translations_model, TranslatedFieldsModel):
            raise TypeError("Expected a TranslatedFieldsModel")

        self.base = base
        self.inherited = False

        if base is None:
            # Make access easier.
            self.root_model = translations_model
            self.root_rel_name = related_name

            # Initial state for lookups
            self._root = None
            self._extensions = []
            self._fields_to_model = OrderedDict()
        else:
            # Inherited situation
            # Still take the base situation as starting point,
            # and register the added translations as extension.
            root = base._root or base
            base.inherited = True
            self._root = root
            self.root_model = root.root_model
            self.root_rel_name = root.root_rel_name

            # This object will amend the caches of the previous object
            # The _extensions list gives access to all inheritance levels where ParlerOptions is defined.
            self._extensions = list(base._extensions)
            self._fields_to_model = base._fields_to_model.copy()

        self.add_meta(ParlerMeta(shared_model, translations_model, related_name))

    def add_meta(self, meta):
        if self.inherited:
            raise RuntimeError("Adding translations afterwards to an already inherited model is not supported yet.")

        self._extensions.append(meta)

        # Fill/amend the caches
        translations_model = meta.model
        for name in translations_model.get_translated_fields():
            self._fields_to_model[name] = translations_model

    def __repr__(self):
        root = self.root
        return "<ParlerOptions: {0}.{1} to {2}{3}>".format(
            root.shared_model.__name__,
            root.rel_name,
            root.model.__name__,
            '' if len(self._extensions) == 1 else ", {0} extensions".format(len(self._extensions))
        )

    @property
    def root(self):
        """
        The top level object in the inheritance chain.
        This is an alias for accessing the first item in the collection.
        """
        return self._extensions[0]

    def __iter__(self):
        """
        Access all :class:`ParlerMeta` objects associated.
        """
        return iter(self._extensions)

    def __getitem__(self, item):
        """
        Get an :class:`ParlerMeta` object by index or model.
        """
        try:
            if isinstance(item, six.integer_types):
                return self._extensions[item]
            elif isinstance(item, six.string_types):
                return self._get_extension_by_related_name(related_name=item)
            else:
                return next(meta for meta in self._extensions if meta.model == item)
        except (StopIteration, IndexError, KeyError):
            raise KeyError("Item '{0}' not found".format(item))

    def __len__(self):
        return len(self._extensions)

    def get_all_models(self):
        """
        Return all translated models associated with the the shared model.
        """
        return [meta.model for meta in self._extensions]

    def get_all_fields(self):
        """
        Return all translated fields associated with this model.
        """
        return list(self._fields_to_model.keys())

    def get_fields_with_model(self):
        """
        Convenience function, return all translated fields with their model.
        """
        return six.iteritems(self._fields_to_model)

    def get_translated_fields(self, related_name=None):
        """
        Return the translated fields of this model.
        By default, the top-level translation is required, unless ``related_name`` is provided.
        """
        # TODO: should be named get_fields() ?
        meta = self._get_extension_by_related_name(related_name)
        return meta.get_translated_fields()

    def get_model_by_field(self, name):
        """
        Find the :class:`TranslatedFieldsModel` that contains the given field.
        """
        try:
            return self._fields_to_model[name]
        except KeyError:
            raise FieldError("Translated field does not exist: '{0}'".format(name))

    def get_model_by_related_name(self, related_name):
        meta = self._get_extension_by_related_name(related_name)
        return meta.model  # extensions have no base set, so root model is correct here.

    def _has_translations_model(self, model):
        return any(meta.model == model for meta in self._extensions)

    def _has_translations_field(self, name):
        return any(meta.rel_name == name for meta in self._extensions)

    def _get_extension_by_field(self, name):
        """
        Find the ParlerOptions object that corresponds with the given translated field.
        """
        if name is None:
            raise TypeError("Expected field name")

        # Reuse existing lookups.
        tr_model = self.get_model_by_field(name)
        for meta in self._extensions:
            if meta.model == tr_model:
                return meta

    def _get_extension_by_related_name(self, related_name):
        """
        Find which model is connected to a given related name.
        If the related name is ``None``, the :attr:`root_model` will be returned.
        """
        if related_name is None:
            return self._extensions[0]

        for meta in self._extensions:
            if meta.rel_name == related_name:
                return meta

        raise ValueError("No translated model of '{0}' has a reverse name of '{1}'".format(
            self.root.shared_model.__name__, related_name
        ))

    def _split_fields(self, **fields):
        # Split fields over their translated models.
        for meta in self._extensions:
            model_fields = {}
            for field in meta.model.get_translated_fields():
                try:
                    model_fields[field] = fields[field]
                except KeyError:
                    pass

            yield (meta, model_fields)
