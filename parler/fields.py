"""
Model fields
"""
from django.db.models.fields import Field


# TODO: inherit RelatedField?
class TranslatedField(object):
    """
    Proxy field attached to a model.

    The field is automatically added to the shared model.
    However, this can be assigned manually to be more explicit, or to pass the ``any_language`` value.
    The ``any_language=True`` option causes the attribute to always return a translated value,
    even when the current language and fallback are missing.
    This can be useful for "title" attributes for example.

    Example::
        from django.db import models
        from parler.models import TranslatableModel, TranslatedFieldsModel

        class MyModel(TranslatableModel):
            title = TranslatedField(any_language=True)
            slug = TranslatedField()   # Optional, but explicitly mentioned

        # Manual model class
        class MyModelTranslation(TranslatedFieldsModel):
            master = models.ForeignKey(MyModel, null=True)
            title = models.CharField("Title", max_length=200)
            slug = models.SlugField("Slug")
    """
    def __init__(self, any_language=False):
        self.model = None
        self.name = None
        self.any_language = any_language

    def contribute_to_class(self, cls, name):
        #super(TranslatedField, self).contribute_to_class(cls, name)
        self.model = cls
        self.name = name

        # Add the proxy attribute
        setattr(cls, self.name, TranslatedFieldDescriptor(self))


class TranslatedFieldDescriptor(object):
    """
    Descriptor for translated attributes.

    This attribute proxies all get/set calls to the translated model.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if not instance:
            # Return the class attribute when asked for by the admin.
            return self

        # Auto create is useless for __get__, will return empty titles everywhere.
        # Better use a fallback instead, just like gettext does.
        translation = None
        try:
            translation = instance._get_translated_model(use_fallback=True)
        except instance._translations_model.DoesNotExist as e:
            if self.field.any_language:
                translation = instance._get_any_translated_model()  # returns None on error.

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
        translation = instance._get_translated_model(use_fallback=False, auto_create=True)
        setattr(translation, self.field.name, value)

    def __delete__(self, instance):
        # No autocreate or fallback, as this is delete.
        # Rather blow it all up when the attribute doesn't exist.
        # Similar to getting a KeyError on `del dict['UNKNOWN_KEY']`
        translation = instance._get_translated_model()
        delattr(translation, self.field.name)

    def __repr__(self):
        return "<{0} for {1}.{2}>".format(self.__class__.__name__, self.field.model.__name__, self.field.name)


class LanguageCodeDescriptor(object):
    """
    This is the property to access the ``language_code`` in the ``TranslatableModel``.
    """
    def __get__(self, instance, instance_type=None):
        if not instance:
            raise AttributeError("language_code must be accessed via instance")

        return instance._current_language

    def __set__(self, instance, value):
        raise AttributeError("The 'language_code' attribute cannot be changed directly! Use the set_current_language() method instead.")

    def __delete__(self, instance):
        raise AttributeError("The 'language_code' attribute cannot be deleted!")


try:
    from south.modelsinspector import add_ignored_fields
except ImportError:
    pass
else:
    _name_re = "^" + __name__.replace(".", "\.")
    add_ignored_fields((
        _name_re + "\.TranslatedField",
    ))
