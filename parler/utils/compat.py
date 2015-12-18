"""
Django compatibility features
"""
from django.db import transaction, models

__all__ = (
    'transaction_atomic',
    'add_preserved_filters',
    'with_metaclass',
    'HideChoicesCharField',
)

# New transaction support in Django 1.6
try:
    transaction_atomic = transaction.atomic
except AttributeError:
    transaction_atomic = transaction.commit_on_success


# Preserving admin form filters when adding parameters to the URL
try:
    # Django 1.6 supports this, and django-parler also applies this fix.
    from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
except ImportError:
    # Django <1.6 does not preserve filters
    def add_preserved_filters(context, form_url):
        return form_url


def with_metaclass(meta, *bases):
    # Function from python-future and jinja2. License: BSD.
    # Allow consistent behaviours across all django versions
    # Also avoids a temporary intermediate class
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__

        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass('temporary_class', None, {})


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

    def south_field_triple(self):
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)
        return ('django.db.models.fields.CharField', args, kwargs)

try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([], ["^" + __name__.replace(".", "\.") + "\.HideChoicesCharField"])
