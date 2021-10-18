"""
The signals exist to make it easier to connect to automatically generated translation models.

To run additional code after saving, consider overwriting
:func:`~parler.models.TranslatableModel.save_translation` instead.
Use the signals as last resort, or to maintain separation of concerns.
"""
from django.dispatch import Signal

pre_translation_init = Signal()
post_translation_init = Signal()

pre_translation_save = Signal()
post_translation_save = Signal()

pre_translation_delete = Signal()
post_translation_delete = Signal()
