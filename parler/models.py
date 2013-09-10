"""
Simple but effective translation support.

Integrating *django-hvad* (v0.3) turned out to be really hard,
as it changes the behavior of the QuerySet iterator, manager methods
and model metaclass which *django-polymorphic* also rely on.
The following is a "crude, but effective" way to introduce multilingual support.

Added on top of that, the API-suger is provided, similar to what django-hvad has.
It's possible to create the translations model manually,
or let it be created dynamically when using the :class:`TranslatedFields` field.
"""
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor
from django.utils.translation import get_language
from parler.fields import TranslatedField, LanguageCodeDescriptor
from parler.managers import TranslatableManager
from parler.utils.i18n import normalize_language_code, get_language_settings
import sys
import logging

logger = logging.getLogger(__name__)



class TranslationDoesNotExist(object):
    """
    A tagging interface to detect missing translations.
    """
    pass


def create_translations_model(model, related_name, meta, **fields):
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
    meta['unique_together'] = list(meta.get('unique_together', [])) + [('language_code', 'master')]

    # Create inner Meta class
    Meta = type('Meta', (object,), meta)
    if not hasattr(Meta, 'db_table'):
        Meta.db_table = model._meta.db_table + '_translation'
    Meta.app_label = model._meta.app_label
    name = '{0}_Translation'.format(model.__name__)

    attrs = {}
    attrs.update(fields)
    attrs['Meta'] = Meta
    attrs['__module__'] = model.__module__
    attrs['objects'] = models.Manager()
    attrs['master'] = models.ForeignKey(model, related_name=related_name, editable=False, null=True)

    # Create and return the new model
    translations_model = TranslatedFieldsModelBase(name, (TranslatedFieldsModel,), attrs)
    translations_model.DoesNotExist = type('DoesNotExist', (TranslationDoesNotExist, model.DoesNotExist, translations_model.DoesNotExist,), {})

    # Register it as a global in the shared model's module.
    # This is needed so that Translation model instances, and objects which refer to them, can be properly pickled and unpickled.
    # The Django session and caching frameworks, in particular, depend on this behaviour.
    mod = sys.modules[model.__module__]
    setattr(mod, name, translations_model)

    return translations_model


class TranslatedFields(object):
    """
    Wrapper class to define translated fields on a model.

    The field name becomes the related name of the :class:`TranslatedFieldsModel` subclass.

    Example::
        from django.db import models
        from parler.models import TranslatableModel, TranslatedFields

        class MyModel(TranslatableModel):
            translations = TranslatedFields(
                title = models.CharField("Title", max_lenght=200)
            )
    """
    def __init__(self, meta=None, **fields):
        self.fields = fields
        self.meta = meta

    def contribute_to_class(self, cls, name):
        # Called from django.db.models.base.ModelBase.__new__
        translations_model = create_translations_model(cls, name, self.meta, **self.fields)

        # The metaclass (TranslatedFieldsModelBase) should configure this already:
        assert cls._translations_model == translations_model
        assert cls._translations_field == name



class TranslatableModel(models.Model):
    """
    Base model class to handle translations.
    """

    # Consider these fields "protected" or "internal" attributes.
    # Not part of the public API, but used internally in the class hierarchy.
    _translations_field = None
    _translations_model = None

    language_code = LanguageCodeDescriptor()

    # change the default manager to the translation manager
    objects = TranslatableManager()

    class Meta:
        abstract = True


    def __init__(self, *args, **kwargs):
        # Still allow to pass the translated fields (e.g. title=...) to this function.
        translated_kwargs = {}
        current_language = None
        if kwargs:
            current_language = kwargs.get('_current_language', None)
            for field in self._translations_model.get_translated_fields():
                try:
                    translated_kwargs[field] = kwargs.pop(field)
                except KeyError:
                    pass

        # Run original Django model __init__
        super(TranslatableModel, self).__init__(*args, **kwargs)

        self._translations_cache = {}
        self._current_language = normalize_language_code(current_language or get_language())  # What you used to fetch the object is what you get.

        # Assign translated args manually.
        if translated_kwargs:
            translation = self._get_translated_model(auto_create=True)
            for field, value in translated_kwargs.iteritems():
                setattr(translation, field, value)

            # Check if other translations were also modified
            for code, obj in self._translations_cache.iteritems():
                if code != translation.language_code and obj.is_modified:
                    obj.save()


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


    def has_translation(self, language_code=None):
        """
        Return whether a translation for the given language exists.
        Defaults to the current language code.
        """
        if language_code is None:
            language_code = self._current_language

        try:
            # Check the cache directly, and the answer is known.
            return self._translations_cache[language_code] is not None
        except KeyError:
            try:
                # Fetch from DB, fill the cache.
                self._get_translated_model(language_code, use_fallback=False, auto_create=False)
            except self._translations_model.DoesNotExist:
                return False
            else:
                return True


    def get_available_languages(self):
        """
        Return the language codes of all translated variations.
        """
        return self._translations_model.objects.filter(master=self).values_list('language_code', flat=True)


    def _get_translated_model(self, language_code=None, use_fallback=False, auto_create=False):
        """
        Fetch the translated fields model.
        """
        if not self._translations_model or not self._translations_field:
            raise ImproperlyConfigured("No translation is assigned to the current model!")

        if not language_code:
            language_code = self._current_language

        # 1. fetch the object from the cache
        try:
            object = self._translations_cache[language_code]

            # If cached object indicates the language doesn't exist, need to query the fallback.
            if object is not None:
                return object
        except KeyError:
            # 2. No cache, need to query
            # Get via self.TRANSLATIONS_FIELD.get(..) so it also uses the prefetch/select_related cache.
            accessor = getattr(self, self._translations_field)
            try:
                object = accessor.get(language_code=language_code)
            except self._translations_model.DoesNotExist:
                pass
            else:
                self._translations_cache[language_code] = object
                return object

        # Not in cache, or default.
        # Not fetched from DB

        # 3. Auto create?
        if auto_create:
            # Auto create policy first (e.g. a __set__ call)
            object = self._translations_model(
                language_code=language_code,
                master=self  # ID might be None at this point
            )
            self._translations_cache[language_code] = object
            return object

        # 4. Fallback?
        fallback_msg = None
        lang_dict = get_language_settings(language_code)

        if use_fallback and (lang_dict['fallback'] != language_code):
            # Jump to fallback language, return directly.
            # Don't cache under this language_code
            self._translations_cache[language_code] = None   # explicit marker that language query was tried before.
            try:
                return self._get_translated_model(lang_dict['fallback'], use_fallback=False, auto_create=auto_create)
            except self._translations_model.DoesNotExist:
                fallback_msg = u" (tried fallback {0})".format(lang_dict['fallback'])

        # None of the above, bail out!
        raise self._translations_model.DoesNotExist(
            u"{0} does not have a translation for the current language!\n"
            u"{0} ID #{1}, language={2}{3}".format(self._meta.verbose_name, self.pk, language_code, fallback_msg or ''
        ))


    def save(self, *args, **kwargs):
        super(TranslatableModel, self).save(*args, **kwargs)
        self.save_translations()


    def save_translations(self):
        # Also save translated strings.
        translations = self._get_translated_model()
        if translations.is_modified:
            if not translations.master_id:  # Might not exist during first construction
                translations.master = self
            translations.save()


class TranslatedFieldsModelBase(ModelBase):
    """
    Meta-class for the translated fields model.

    It performs the following steps:
    - It validates the 'master' field, in case it's added manually.
    - It tells the original model to use this model for translations.
    - It adds the proxy attributes to the shared model.
    """
    def __new__(mcs, name, bases, attrs):
        new_class = super(TranslatedFieldsModelBase, mcs).__new__(mcs, name, bases, attrs)
        if bases[0] == models.Model:
            return new_class

        # Validate a manually configured class.
        shared_model = _validate_master(new_class)

        # Link the translated fields model to the shared model.
        shared_model._translations_model = new_class
        shared_model._translations_field = new_class.master.field.rel.related_name

        # Add wrappers for all translated fields to the shared models.
        new_class.contribute_translations(shared_model)

        return new_class


def _validate_master(new_class):
    """
    Check whether the 'master' field on a TranslatedFieldsModel is correctly configured.
    """
    if not new_class.master or not isinstance(new_class.master, ReverseSingleRelatedObjectDescriptor):
        msg = "{0}.master should be a ForeignKey to the shared table.".format(new_class.__name__)
        logger.error(msg)
        raise TypeError(msg)

    shared_model = new_class.master.field.rel.to
    if not issubclass(shared_model, models.Model):
        # Not supporting models.ForeignKey("tablename") yet. Can't use get_model() as the models are still being constructed.
        msg = "{0}.master should point to a model class, can't use named field here.".format(new_class.__name__)
        logger.error(msg)
        raise TypeError(msg)

    if shared_model._translations_model:
        msg = "The model '{0}' already has an associated translation table!".format(shared_model.__name__)
        logger.error(msg)
        raise TypeError(msg)

    return shared_model



class TranslatedFieldsModel(models.Model):
    """
    Base class for the model that holds the translated fields.
    """
    __metaclass__ = TranslatedFieldsModelBase

    language_code = models.CharField(max_length=15, db_index=True)
    master = None   # FK to shared model.

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(TranslatedFieldsModel, self).__init__(*args, **kwargs)
        self._original_values = self._get_field_values()

    @property
    def is_modified(self):
        return self._original_values != self._get_field_values()

    def save(self, *args, **kwargs):
        super(TranslatedFieldsModel, self).save(*args, **kwargs)
        self._original_values = self._get_field_values()

    def _get_field_values(self):
        # Return all field values in a consistent (sorted) manner.
        return [getattr(self, field) for field in self._meta.get_all_field_names()]

    @classmethod
    def get_translated_fields(self):
        fields = self._meta.get_all_field_names()
        fields.remove('language_code')
        fields.remove('master')
        fields.remove('id')   # exists with deferred objects that .only() queries create.
        return fields

    @classmethod
    def contribute_translations(cls, shared_model):
        """
        Add the proxy attributes to the shared model.
        """
        for name in cls.get_translated_fields():
            try:
                # Note that the descriptor even proxies this request, so it should return our field.
                field = getattr(shared_model, name)
            except AttributeError:
                # Add the proxy field for the shared field.
                TranslatedField().contribute_to_class(shared_model, name)
            else:
                if not isinstance(field, models.Field) or field.model is not cls:
                    raise TypeError("The model '{0}' already has a field named '{1}'".format(shared_model.__name__, name))

    def __unicode__(self):
        return unicode(self.pk)

    def __repr__(self):
        return "<{0}: #{1}, {2}, master: #{3}>".format(
            self.__class__.__name__, self.pk, self.language_code, self.master_id
        )
