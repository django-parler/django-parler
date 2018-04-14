"""
All fields that are attached to the models.

The core design of django-parler is to attach descriptor fields
to the shared model, which then proxies the get/set calls to the translated model.

The :class:`TranslatedField` objects are automatically added to the shared model,
but may be added explicitly as well. This also allows to set the ``any_language`` configuration option.
It's also useful for abstract models; add a :class:`TranslatedField` to
indicate that the derived model is expected to provide that translatable field.
"""
from __future__ import unicode_literals

import django
from django.forms.forms import pretty_name


# TODO: inherit RelatedField?
class TranslatedField(object):
    """
    Proxy field attached to a model.

    The field is automatically added to the shared model.
    However, this can be assigned manually to be more explicit, or to pass the ``any_language`` value.
    The ``any_language=True`` option causes the attribute to always return a translated value,
    even when the current language and fallback are missing.
    This can be useful for "title" attributes for example.

    Example:

    .. code-block:: python

        from django.db import models
        from parler.models import TranslatableModel, TranslatedFieldsModel

        class MyModel(TranslatableModel):
            title = TranslatedField(any_language=True)  # Add with any-fallback support
            slug = TranslatedField()                    # Optional, but explicitly mentioned


        class MyModelTranslation(TranslatedFieldsModel):
            # Manual model class:
            master = models.ForeignKey(MyModel, related_name='translations', null=True)
            title = models.CharField("Title", max_length=200)
            slug = models.SlugField("Slug")
    """

    def __init__(self, any_language=False):
        self.model = None
        self.name = None
        self.any_language = any_language
        self._meta = None

    def contribute_to_class(self, cls, name, **kwargs):
        #super(TranslatedField, self).contribute_to_class(cls, name)
        self.model = cls
        self.name = name

        # Add the proxy attribute
        setattr(cls, self.name, TranslatedFieldDescriptor(self))

    @property
    def meta(self):
        if self._meta is None:
            self._meta = self.model._parler_meta._get_extension_by_field(self.name)
        return self._meta


class TranslatedFieldDescriptor(object):
    """
    Descriptor for translated attributes.

    This attribute proxies all get/set calls to the translated model.
    """

    def __init__(self, field):
        """
        :type field: TranslatedField
        """
        self.field = field

    def __get__(self, instance, instance_type=None):
        if not instance:
            # Return the class attribute when asked for by the admin.
            return self

        # Auto create is useless for __get__, will return empty titles everywhere.
        # Better use a fallback instead, just like gettext does.
        translation = None
        meta = self.field.meta
        try:
            translation = instance._get_translated_model(use_fallback=True, meta=meta)
        except meta.model.DoesNotExist as e:
            if self.field.any_language:
                translation = instance._get_any_translated_model(meta=meta)  # returns None on error.

            if translation is None:
                # Improve error message
                e.args = ("{1}\nAttempted to read attribute {0}.".format(self.field.name, e.args[0]),)
                raise

        return getattr(translation, self.field.name)

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("{0} must be accessed via instance".format(self.field.opts.object_name))

        # When assigning the property, assign to the current language.
        # No fallback is used in this case.
        translation = instance._get_translated_model(use_fallback=False, auto_create=True, meta=self.field.meta)
        setattr(translation, self.field.name, value)

    def __delete__(self, instance):
        # No autocreate or fallback, as this is delete.
        # Rather blow it all up when the attribute doesn't exist.
        # Similar to getting a KeyError on `del dict['UNKNOWN_KEY']`
        translation = instance._get_translated_model(meta=self.field.meta)
        delattr(translation, self.field.name)

    def __repr__(self):
        return "<{0} for {1}.{2}>".format(self.__class__.__name__, self.field.model.__name__, self.field.name)

    @property
    def short_description(self):
        """
        Ensure that the admin ``list_display`` renders the correct verbose name for translated fields.

        The :func:`~django.contrib.admin.utils.label_for_field` function
        uses :func:`~django.db.models.Options.get_field_by_name` to find the find and ``verbose_name``.
        However, for translated fields, this option does not exist,
        hence it falls back to reading the attribute and trying ``short_description``.
        Ideally, translated fields should also appear in this list, to be treated like regular fields.
        """
        translations_model = self.field.meta.model
        if translations_model is None:
            # This only happens with abstract models. The code is accessing the descriptor at the base model directly,
            # not the upgraded descriptor version that contribute_translations() installed.
            # Fallback to what the admin label_for_field() would have done otherwise.
            return pretty_name(self.field.name)

        if django.VERSION >= (1, 8):
            field = translations_model._meta.get_field(self.field.name)
        else:
            field = translations_model._meta.get_field_by_name(self.field.name)[0]

        return field.verbose_name


class LanguageCodeDescriptor(object):
    """
    This is the property to access the ``language_code`` in the ``TranslatableModel``.
    """

    def __get__(self, instance, instance_type=None):
        if not instance:
            return self

        return instance._current_language

    def __set__(self, instance, value):
        raise AttributeError("The 'language_code' attribute cannot be changed directly! Use the set_current_language() method instead.")

    def __delete__(self, instance):
        raise AttributeError("The 'language_code' attribute cannot be deleted!")
