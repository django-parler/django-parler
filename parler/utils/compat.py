"""
Django compatibility features
"""
from django.db import transaction

__all__ = (
    'transaction_atomic',
    'add_preserved_filters',
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
    """Create a base class with a metaclass."""
    # from six v1.7.1, to allow consistent behaviours across all django versions
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})
