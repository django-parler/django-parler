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

        def __str__(self):
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

        def __str__(self):
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
import sys
import warnings
from collections import OrderedDict, defaultdict

from django.conf import settings
from django.core.exceptions import (
    FieldError,
    ImproperlyConfigured,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import models, router
from django.db.models.base import ModelBase
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
)
from django.utils.encoding import force_str
from django.utils.functional import lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from parler import signals
from parler.cache import (
    MISSING,
    _cache_translation,
    _cache_translation_needs_fallback,
    _delete_cached_translation,
    _delete_cached_translations,
    get_cached_translated_field,
    get_cached_translation,
    is_missing,
)
from parler.fields import (
    LanguageCodeDescriptor,
    TranslatedField,
    TranslatedFieldDescriptor,
    TranslationsForeignKey,
    _validate_master,
)
from parler.managers import TranslatableManager
from parler.utils import compat
from parler.utils.i18n import (
    get_language,
    get_language_settings,
    get_language_title,
    get_null_language_error,
    normalize_language_code,
)

__all__ = (
    "TranslatableModelMixin",
    "TranslatableModel",
    "TranslatedFields",
    "TranslatedFieldsModel",
    "TranslatedFieldsModelBase",
    "TranslationDoesNotExist",
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


_lazy_verbose_name = lazy(lambda x: gettext("{0} Translation").format(x._meta.verbose_name), str)


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
        raise TypeError(
            f"Can't create TranslatedFieldsModel for abstract class {shared_model.__name__}"
        )

    # Define inner Meta class
    meta["app_label"] = shared_model._meta.app_label
    meta["db_tablespace"] = shared_model._meta.db_tablespace
    meta["managed"] = shared_model._meta.managed
    meta["unique_together"] = list(meta.get("unique_together", [])) + [("language_code", "master")]
    meta.setdefault("db_table", f"{shared_model._meta.db_table}_translation")
    meta.setdefault("verbose_name", _lazy_verbose_name(shared_model))

    # Avoid creating permissions for the translated model, these are not used at all.
    # This also avoids creating lengthy permission names above 50 chars.
    meta.setdefault("default_permissions", ())

    # Define attributes for translation table
    name = str(f"{shared_model.__name__}Translation")  # makes it bytes, for type()

    attrs = {}
    attrs.update(fields)
    attrs["Meta"] = type("Meta", (object,), meta)
    attrs["__module__"] = shared_model.__module__
    attrs["objects"] = models.Manager()
    attrs["master"] = TranslationsForeignKey(
        shared_model,
        related_name=related_name,
        editable=False,
        null=True,
        on_delete=models.CASCADE,
    )

    # Create and return the new model
    translations_model = TranslatedFieldsModelBase(name, (TranslatedFieldsModel,), attrs)

    # Register it as a global in the shared model's module.
    # This is needed so that Translation model instances, and objects which refer to them, can be properly pickled and unpickled.
    # The Django session and caching frameworks, in particular, depend on this behaviour.
    mod = sys.modules[shared_model.__module__]
    setattr(mod, name, translations_model)

    return translations_model


class TranslatedFields:
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
    Hence, accessing ``MyModel.translations.related.related_model`` returns the original model
    via the :class:`django.db.models.related.RelatedObject` class.

    ..
       To fetch the attribute, you can also query the Parler metadata:
       MyModel._parler_meta.get_model_by_related_name('translations')

    :param meta: A dictionary of `Meta` options, passed to the :class:`TranslatedFieldsModel`
        instance.

        Example:

        .. code-block:: python

            class MyModel(TranslatableModel):
                translations = TranslatedFields(
                    title = models.CharField("Title", max_length=200),
                    slug = models.SlugField("Slug"),
                    meta = {'unique_together': [('language_code', 'slug')]},
                )

    """

    def __init__(self, meta=None, **fields):
        self.fields = fields
        self.meta = meta
        self.name = None

    def contribute_to_class(self, cls, name, **kwargs):
        # Called from django.db.models.base.ModelBase.__new__
        self.name = name
        create_translations_model(cls, name, self.meta, **self.fields)


class TranslatableModelMixin:
    """
    Base model mixin class to handle translations.

    All translatable fields will appear on this model, proxying the calls to the :class:`TranslatedFieldsModel`.
    """

    #: Access to the metadata of the translatable model
    #: :type: ParlerOptions
    _parler_meta = None  # type: ParlerOptions

    #: Access to the language code
    language_code = LanguageCodeDescriptor()

    def __init__(self, *args, **kwargs):
        # Still allow to pass the translated fields (e.g. title=...) to this function.
        translated_kwargs = {}
        current_language = None
        if kwargs:
            current_language = kwargs.pop("_current_language", None)
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
        super().__init__(*args, **kwargs)

        # Assign translated args manually.
        self._translations_cache = defaultdict(dict)
        self._current_language = normalize_language_code(
            current_language or get_language()
        )  # What you used to fetch the object is what you get.

        if translated_kwargs:
            self._set_translated_fields(self._current_language, **translated_kwargs)

    def _set_translated_fields(self, language_code=None, **fields):
        """
        Assign fields to the translated models.
        """
        objects = []  # no generator, make sure objects are all filled first
        for parler_meta, model_fields in self._parler_meta._split_fields(**fields):
            translation = self._get_translated_model(
                language_code=language_code, auto_create=True, meta=parler_meta
            )
            for field, value in model_fields.items():
                try:
                    setattr(translation, field, value)
                except TypeError:
                    # TypeError signals a many to many field. We can't set it like the other attributes, so
                    # add to our own glued variable.
                    deferred_many_to_many = getattr(translation, "deferred_many_to_many", {})
                    deferred_many_to_many[field] = value
                    setattr(translation, "deferred_many_to_many", deferred_many_to_many)

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
        if language_code is None:
            raise ValueError(get_null_language_error())

        meta = self._parler_meta
        if self._translations_cache[meta.root_model].get(
            language_code, None
        ):  # MISSING evaluates to False too
            raise ValueError(f"Translation already exists: {language_code}")

        # Save all fields in the proper translated model.
        for translation in self._set_translated_fields(language_code, **fields):
            self.save_translation(translation)

    def delete_translation(self, language_code, related_name=None):
        """
        Delete a translation from a model.

        :param language_code: The language to remove.
        :param related_name: If given, only the model matching that related_name is removed.
        """
        if language_code is None:
            raise ValueError(get_null_language_error())

        if related_name is None:
            metas = self._parler_meta
        else:
            metas = [self._parler_meta[related_name]]

        num_deleted = 0
        for meta in metas:
            try:
                translation = self._get_translated_model(language_code, meta=meta)
            except meta.model.DoesNotExist:
                continue

            # By using the regular model delete, the cache is properly cleared
            # (via _delete_cached_translation) and signals are emitted.
            translation.delete()
            num_deleted += 1

            # Clear other local caches
            try:
                del self._translations_cache[meta.model][language_code]
            except KeyError:
                pass
            try:
                del self._prefetched_objects_cache[meta.rel_name]
            except (AttributeError, KeyError):
                pass

        if not num_deleted:
            raise ValueError(f"Translation does not exist: {language_code}")

        return num_deleted

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
        .. deprecated:: 1.5
           Use :func:`get_fallback_languages` instead.
        """
        fallbacks = self.get_fallback_languages()
        return fallbacks[0] if fallbacks else None

    def get_fallback_languages(self):
        """
        Return the fallback language codes,
        which are used in case there is no translation for the currently active language.
        """
        lang_dict = get_language_settings(self._current_language)
        fallbacks = [lang for lang in lang_dict["fallbacks"] if lang != self._current_language]
        return fallbacks or []

    def has_translation(self, language_code=None, related_name=None):
        """
        Return whether a translation for the given language exists.
        Defaults to the current language code.

        .. versionadded 1.2 Added the ``related_name`` parameter.
        """
        if language_code is None:
            language_code = self._current_language
            if language_code is None:
                raise ValueError(get_null_language_error())

        meta = self._parler_meta._get_extension_by_related_name(related_name)

        try:
            # Check the local cache directly, and the answer is known.
            # NOTE this may also return newly auto created translations which are not saved yet.
            return not is_missing(self._translations_cache[meta.model][language_code])
        except KeyError:
            # If there is a prefetch, will be using that.
            # However, don't assume the prefetch contains all possible languages.
            # With Django 1.8, there are custom Prefetch objects.
            # TODO: improve this, detect whether this is the case.
            if language_code in self._read_prefetched_translations(meta=meta):
                return True

            # Try to fetch from the cache first.
            # If the cache returns the fallback, it means the original does not exist.
            object = get_cached_translation(
                self, language_code, related_name=related_name, use_fallback=True
            )
            if object is not None:
                return object.language_code == language_code

            try:
                # Fetch from DB, fill the cache.
                self._get_translated_model(
                    language_code, use_fallback=False, auto_create=False, meta=meta
                )
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
            # TODO: this will break when using custom Django 1.8 Prefetch objects?
            db_languages = sorted(obj.language_code for obj in prefetch)
        else:
            qs = self._get_translated_queryset(meta=meta)
            db_languages = qs.values_list("language_code", flat=True).order_by("language_code")

        if include_unsaved:
            local_languages = (
                k for k, v in self._translations_cache[meta.model].items() if not is_missing(v)
            )
            return list(set(db_languages) | set(local_languages))
        else:
            return db_languages

    def get_translation(self, language_code, related_name=None):
        """
        Fetch the translated model
        """
        meta = self._parler_meta._get_extension_by_related_name(related_name)
        return self._get_translated_model(language_code, meta=meta)

    def _get_translated_model(
        self, language_code=None, use_fallback=False, auto_create=False, meta=None
    ):
        """
        Fetch the translated fields model.
        """
        if self._parler_meta is None:
            raise ImproperlyConfigured("No translation is assigned to the current model!")
        if self._translations_cache is None:
            raise RuntimeError(
                "Accessing translated fields before super.__init__() is not possible."
            )

        if not language_code:
            language_code = self._current_language
            if language_code is None:
                raise ValueError(get_null_language_error())

        if meta is None:
            meta = self._parler_meta.root  # work on base model by default

        local_cache = self._translations_cache[meta.model]

        # 1. fetch the object from the local cache
        try:
            object = local_cache[language_code]

            # If cached object indicates the language doesn't exist, need to query the fallback.
            if not is_missing(object):
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
                    object = get_cached_translation(
                        self, language_code, related_name=meta.rel_name, use_fallback=use_fallback
                    )
                    if object is not None:
                        # Track in local cache
                        if object.language_code != language_code:
                            local_cache[language_code] = MISSING  # Set fallback marker
                        local_cache[object.language_code] = object
                        return object
                    elif is_missing(local_cache.get(language_code, None)):
                        # If get_cached_translation() explicitly set the "does not exist" marker,
                        # there is no need to try a database query.
                        pass
                    else:
                        # 2.3, fetch from database
                        try:
                            object = self._get_translated_queryset(meta).get(
                                language_code=language_code
                            )
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
            kwargs = {
                "language_code": language_code,
            }
            if self.pk and not self._state.adding:
                # ID might be None at this point, and Django does not allow that.
                kwargs["master"] = self

            object = meta.model(**kwargs)
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

        fallback_choices = [lang_dict["code"]] + list(lang_dict["fallbacks"])
        if use_fallback and fallback_choices:
            # Jump to fallback language, return directly.
            # Don't cache under this language_code
            for fallback_lang in fallback_choices:
                if (
                    fallback_lang == language_code
                ):  # Skip the current language, could also be fallback 1 of 2 choices
                    continue

                try:
                    return self._get_translated_model(
                        fallback_lang, use_fallback=False, auto_create=auto_create, meta=meta
                    )
                except meta.model.DoesNotExist:
                    pass

            fallback_msg = " (tried fallbacks {})".format(", ".join(lang_dict["fallbacks"]))

        # None of the above, bail out!
        raise meta.model.DoesNotExist(
            "{0} does not have a translation for the current language!\n"
            "{0} ID #{1}, language={2}{3}".format(
                self._meta.verbose_name, self.pk, language_code, fallback_msg or ""
            )
        )

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
            check_languages = [self._current_language] + self.get_fallback_languages()
            try:
                for fallback_lang in check_languages:
                    trans = local_cache.get(fallback_lang, None)
                    if trans and not is_missing(trans):
                        return trans
                return next(t for t in local_cache.values() if not is_missing(t))
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

        accessor = getattr(self, meta.rel_name)  # RelatedManager
        return accessor.get_queryset()

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

    def _read_prefetched_translations(self, meta=None):
        # Load the prefetched translations into the local cache.
        if meta is None:
            meta = self._parler_meta.root

        local_cache = self._translations_cache[meta.model]
        prefetch = self._get_prefetched_translations(meta=meta)

        languages_seen = []
        if prefetch is not None:
            for translation in prefetch:
                lang = translation.language_code
                languages_seen.append(lang)
                if lang not in local_cache or is_missing(local_cache[lang]):
                    local_cache[lang] = translation

        return languages_seen

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Makes no sense to add these for translated model
        # Even worse: mptt 0.7 injects this parameter when it avoids updating the lft/rgt fields,
        # but that misses all the translated fields.
        kwargs.pop("update_fields", None)

        self.save_translations(*args, **kwargs)

    def delete(self, using=None):
        _delete_cached_translations(self)
        return super().delete(using)

    def validate_unique(self, exclude=None):
        """
        Also validate the unique_together of the translated model.
        """
        # This is called from ModelForm._post_clean() or Model.full_clean()
        errors = {}
        try:
            super().validate_unique(exclude=exclude)
        except ValidationError as e:
            errors = e.error_dict

        for local_cache in self._translations_cache.values():
            for translation in local_cache.values():
                if is_missing(translation):  # Skip fallback markers
                    continue

                try:
                    translation.validate_unique(exclude=exclude)
                except ValidationError as e:
                    errors.update(e.error_dict)

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
                if is_missing(translation):  # Skip fallback markers
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
        if translation.pk is None or translation.is_modified:
            if not translation.master_id:  # Might not exist during first construction
                translation._state.db = self._state.db
                translation.master = self
            translation.save(*args, **kwargs)

        # Save the many to many fields
        deferred_many_to_many = getattr(translation, "deferred_many_to_many", {})
        if deferred_many_to_many:
            for fieldname, value in deferred_many_to_many.items():
                getattr(translation, fieldname).set(value)
            translation.save()

    def safe_translation_getter(self, field, default=None, language_code=None, any_language=False):
        """
        Fetch a translated property, and return a default value
        when both the translation and fallback language are missing.

        When ``any_language=True`` is used, the function also looks
        into other languages to find a suitable value. This feature can be useful
        for "title" attributes for example, to make sure there is at least something being displayed.
        Also consider using ``field = TranslatedField(any_language=True)`` in the model itself,
        to make this behavior the default for the given field.

        .. versionchanged 1.5:: The *default* parameter may also be a callable.
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
                try:
                    return getattr(translation, field)
                except KeyError:
                    pass

        if callable(default):
            return default()
        else:
            return default

    def refresh_from_db(self, *args, **kwargs):
        super().refresh_from_db(*args, **kwargs)
        _delete_cached_translations(self)
        self._translations_cache.clear()

    refresh_from_db.alters_data = True


class TranslatableModel(TranslatableModelMixin, models.Model):
    """
    Base model class to handle translations.

    All translatable fields will appear on this model, proxying the calls to the :class:`TranslatedFieldsModel`.
    """

    class Meta:
        abstract = True

    # change the default manager to the translation manager
    objects = TranslatableManager()


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

        new_class = super().__new__(mcs, name, bases, attrs)
        if bases[0] == models.Model:
            return new_class

        # No action in abstract models.
        if new_class._meta.abstract or new_class._meta.proxy:
            return new_class

        if not isinstance(getattr(new_class.master, "field"), TranslationsForeignKey):
            warnings.warn(
                "Please change {}.master to a parler.fields.TranslationsForeignKey field to support translations in "
                "data migrations.".format(new_class._meta.model_name),
                DeprecationWarning,
            )

            # Validate a manually configured class.
            shared_model = _validate_master(new_class)

            # Add wrappers for all translated fields to the shared models.
            new_class.contribute_translations(shared_model)

        return new_class


class TranslatedFieldsModelMixin:
    """
    Base class for the model that holds the translated fields.
    """

    #: The mandatory Foreign key field to the shared model.
    master = None  # FK to shared model.

    def __init__(self, *args, **kwargs):
        signals.pre_translation_init.send(sender=self.__class__, args=args, kwargs=kwargs)
        super().__init__(*args, **kwargs)
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
        return self.__class__.master.field.remote_field.model

    @property
    def related_name(self):
        """
        Returns the related name that this model is known at in the shared model.
        """
        return self.__class__.master.field.remote_field.related_name

    def save_base(self, raw=False, using=None, **kwargs):
        # Not calling translations.activate() or disabling the translation
        # causes get_language() to explicitly return None instead of LANGUAGE_CODE.
        # This helps developers find solutions by bailing out properly.
        #
        # Either use translation.activate() first, or pass the language code explicitly via
        # MyModel.objects.language('en').create(..)
        assert self.language_code is not None, (
            ""
            "No language is set or detected for this TranslatableModelMixin.\n"
            "Is the translations system initialized?"
        )

        # Send the pre_save signal
        using = using or router.db_for_write(self.__class__, instance=self)
        record_exists = self.pk is not None  # Ignoring force_insert/force_update for now.
        if not self._meta.auto_created:
            signals.pre_translation_save.send(
                sender=self.shared_model, instance=self, raw=raw, using=using
            )

        # Perform save
        super().save_base(raw=raw, using=using, **kwargs)
        self._original_values = self._get_field_values()
        _cache_translation(self)

        # Send the post_save signal
        if not self._meta.auto_created:
            signals.post_translation_save.send(
                sender=self.shared_model,
                instance=self,
                created=(not record_exists),
                raw=raw,
                using=using,
            )

    def delete(self, using=None):
        # Send pre-delete signal
        using = using or router.db_for_write(self.__class__, instance=self)
        if not self._meta.auto_created:
            signals.pre_translation_delete.send(
                sender=self.shared_model, instance=self, using=using
            )

        super().delete(using=using)
        _delete_cached_translation(self)

        # Send post-delete signal
        if not self._meta.auto_created:
            signals.post_translation_delete.send(
                sender=self.shared_model, instance=self, using=using
            )

    def _get_field_names(self):
        # Use the new Model._meta API.
        return [
            field.get_attname()
            for field in self._meta.get_fields()
            if not field.is_relation or field.many_to_one
        ]

    def _get_field_values(self):
        # Use the new Model._meta API.
        return [
            getattr(self, field.get_attname())
            for field in self._meta.get_fields()
            if not field.is_relation or field.many_to_one
        ]

    @classmethod
    def get_translated_fields(cls, include_m2m=True):
        res = [
            f.name
            for f in cls._meta.local_fields
            if f.name not in ("language_code", "master", "id")
        ]
        if include_m2m:
            res += [
                f.name
                for f in cls._meta.local_many_to_many
                if f.name not in ("language_code", "master", "id")
            ]
        return res

    @classmethod
    def contribute_translations(cls, shared_model):
        """
        Add the proxy attributes to the shared model.
        """
        # Instance at previous inheritance level, if set.
        # This is checked for None as some migration files don't use bases=TranslatableModel instead
        try:
            base = shared_model._parler_meta
        except AttributeError:
            raise TypeError(
                f"Translatable model {shared_model} does not appear to inherit from TranslatableModel"
            )

        if base is not None and base[-1].shared_model is shared_model:
            # If a second translations model is added, register it in the same object level.
            base.add_meta(
                ParlerMeta(
                    shared_model=shared_model,
                    translations_model=cls,
                    related_name=cls.master.field.remote_field.related_name,
                )
            )
        else:
            # Place a new _parler_meta at the current inheritance level.
            # It links to the previous base.
            shared_model._parler_meta = ParlerOptions(
                base,
                shared_model=shared_model,
                translations_model=cls,
                related_name=cls.master.field.remote_field.related_name,
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
                    raise TypeError(
                        f"The model '{shared_model.__name__}' already has a field named '{name}'"
                    )

                # When the descriptor was placed on an abstract model,
                # it doesn't point to the real model that holds the translations_model
                # "Upgrade" the descriptor on the class
                if shared_field.field.model is not shared_model:
                    TranslatedField(
                        any_language=shared_field.field.any_language
                    ).contribute_to_class(shared_model, name)

        # Make sure the DoesNotExist error can be detected als shared_model.DoesNotExist too,
        # and by inheriting from AttributeError it makes sure (admin) templates can handle the missing attribute.
        cls.DoesNotExist = type(
            "DoesNotExist",
            (
                TranslationDoesNotExist,
                shared_model.DoesNotExist,
                cls.DoesNotExist,
            ),
            {},
        )

    def __str__(self):
        return force_str(get_language_title(self.language_code))

    def __repr__(self):
        return "<{}: #{}, {}, master: #{}>".format(
            self.__class__.__name__, self.pk, self.language_code, self.master_id
        )


class TranslatedFieldsModel(
    TranslatedFieldsModelMixin, models.Model, metaclass=TranslatedFieldsModelBase
):
    language_code = compat.HideChoicesCharField(
        _("Language"), choices=settings.LANGUAGES, max_length=15, db_index=True
    )

    class Meta:
        abstract = True
        default_permissions = ()


class ParlerMeta:
    """
    Meta data for a single inheritance level.
    """

    def __init__(self, shared_model, translations_model, related_name):
        # Store meta information of *this* level
        self.shared_model = shared_model
        self.model = translations_model
        self.rel_name = related_name

    def get_translated_fields(self, include_m2m=True):
        """
        Return the translated fields of this model.
        """
        # TODO: should be named get_fields() ?
        # root_model always points to the real model for extensions
        return self.model.get_translated_fields(include_m2m=include_m2m)

    def __repr__(self):
        return "<ParlerMeta: {}.{} to {}>".format(
            self.shared_model.__name__, self.rel_name, self.model.__name__
        )


class ParlerOptions:
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
            raise RuntimeError(
                "Adding translations afterwards to an already inherited model is not supported yet."
            )

        self._extensions.append(meta)

        # Fill/amend the caches
        translations_model = meta.model
        for name in translations_model.get_translated_fields():
            self._fields_to_model[name] = translations_model

    def __repr__(self):
        root = self.root
        return "<ParlerOptions: {}.{} to {}{}>".format(
            root.shared_model.__name__,
            root.rel_name,
            root.model.__name__,
            "" if len(self._extensions) == 1 else f", {len(self._extensions)} extensions",
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
            if isinstance(item, int):
                return self._extensions[item]
            elif isinstance(item, str):
                return self._get_extension_by_related_name(related_name=item)
            else:
                return next(meta for meta in self._extensions if meta.model == item)
        except (StopIteration, IndexError, KeyError):
            raise KeyError(f"Item '{item}' not found")

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
        return self._fields_to_model.items()

    def get_translated_fields(self, related_name=None, include_m2m=True):
        """
        Return the translated fields of this model.
        By default, the top-level translation is required, unless ``related_name`` is provided.
        """
        # TODO: should be named get_fields() ?
        meta = self._get_extension_by_related_name(related_name)
        return meta.get_translated_fields(include_m2m=include_m2m)

    def get_model_by_field(self, name):
        """
        Find the :class:`TranslatedFieldsModel` that contains the given field.
        """
        try:
            return self._fields_to_model[name]
        except KeyError:
            raise FieldError(f"Translated field does not exist: '{name}'")

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

        raise ValueError(
            "No translated model of '{}' has a reverse name of '{}'".format(
                self.root.shared_model.__name__, related_name
            )
        )

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
