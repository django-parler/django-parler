"""
The signals exist to make it easier to connect to automatically generated translation models.

To run additional code after saving, consider overwriting
:func:`~parler.models.TranslatableModel.save_translation` instead.
Use the signals as last resort, or to maintain separation of concerns.
"""
from django.dispatch import Signal

pre_translation_init = Signal(providing_args=["instance", "args", "kwargs"])
post_translation_init = Signal(providing_args=["instance"])

pre_translation_save = Signal(providing_args=["instance", "raw", "using"])
post_translation_save = Signal(providing_args=["instance", "raw", "created", "using"])

pre_translation_delete = Signal(providing_args=["instance", "using"])
post_translation_delete = Signal(providing_args=["instance", "using"])
