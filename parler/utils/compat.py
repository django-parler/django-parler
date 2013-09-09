"""
Django compatibility features
"""
from django.db import transaction

__all__ = (
    'transaction_atomic',
)

# New transaction support in Django 1.6
try:
    transaction_atomic = transaction.atomic
except AttributeError:
    transaction_atomic = transaction.commit_on_success
