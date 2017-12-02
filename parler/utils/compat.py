"""
Django compatibility features
"""
from django.db import models

__all__ = (
    'HideChoicesCharField',
)


class HideChoicesCharField(models.CharField):
    # For Django 1.7, hide the 'choices' for a field.

    def deconstruct(self):
        name, path, args, kwargs = models.CharField.deconstruct(self)

        # Hide the fact this model was used.
        if path == __name__ + '.HideChoicesCharField':
            path = 'django.db.models.CharField'
        try:
            del kwargs['choices']
        except KeyError:
            pass

        return name, path, args, kwargs


def get_remote_field(klass):
    try:
        return klass.master.field.remote_field
    except AttributeError:
        # Django <= 1.8 compatibility
        return klass.master.field.rel
