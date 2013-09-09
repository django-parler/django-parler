"""
Model fields
"""
from django.db.models.fields import Field


# TODO: inherit RelatedField?
class TranslatedField(object):
    """
    Proxy field attached to a model.
    This makes sure the Django admin finds an actual field for the translated attribute.
    """
    def __init__(self, name):
        self.name = name

    def contribute_to_class(self, cls, name):
        #super(TranslatedField, self).contribute_to_class(cls, name)
        self.model = cls
        self.name = name

        # Add the descriptor for the m2m relation
        setattr(cls, self.name, TranslatedFieldDescriptor(self))


class TranslatedFieldDescriptor(object):
    """
    Descriptor for translated attributes.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if not instance:
            # Return the class attribute when asked for by the admin.
            return instance_type._translations_model._meta.get_field_by_name(self.field.name)[0]

        # Auto create is useless for __get__, will return empty titles everywhere.
        # Better use a fallback instead, just like gettext does.
        translation = instance._get_translated_model(use_fallback=True)
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


try:
    from south.modelsinspector import add_ignored_fields
except ImportError:
    pass
else:
    _name_re = "^" + __name__.replace(".", "\.")
    add_ignored_fields((
        _name_re + "\.TranslatedField",
    ))
