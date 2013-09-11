from django.dispatch import Signal

pre_translation_init = Signal(providing_args=["instance", "args", "kwargs"])
post_translation_init = Signal(providing_args=["instance"])

pre_translation_save = Signal(providing_args=["instance", "raw", "using", "update_fields"])
post_translation_save = Signal(providing_args=["instance", "raw", "created", "using", "update_fields"])

pre_translation_delete = Signal(providing_args=["instance", "using"])
post_translation_delete = Signal(providing_args=["instance", "using"])
