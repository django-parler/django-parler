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
