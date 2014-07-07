parler.signals module
=====================

.. automodule:: parler.signals
    :members:
    :undoc-members:
    :show-inheritance:

.. currentmodule:: parler.signals


``pre_translation_init``
------------------------

.. data:: parler.signals.pre_translation_init
   :module:

This is called when the translated model is initialized,
like :attr:`~django.db.models.signals.pre_init`.

Arguments sent with this signal:

``sender``
    As above: the model class that just had an instance created.

``instance``
    The actual translated model that's just been created.

``args``
    Any arguments passed to the model.

``kwargs``
    Any keyword arguments passed to the model.


``post_translation_init``
-------------------------

.. data:: parler.signals.post_translation_init
   :module:

This is called when the translated model has been initialized,
like :attr:`~django.db.models.signals.post_init`.

Arguments sent with this signal:

``sender``
    As above: the model class that just had an instance created.

``instance``
    The actual translated model that's just been created.


``pre_translation_save``
------------------------

.. data:: parler.signals.pre_translation_save
   :module:

This is called before the translated model is saved,
like :attr:`~django.db.models.signals.pre_save`.

Arguments sent with this signal:

``sender``
    The model class.

``instance``
    The actual translated model instance being saved.

``raw``
    ``True`` when the model is being created by a fixture.

``using``
    The database alias being used


``post_translation_save``
-------------------------

.. data:: parler.signals.post_translation_save
   :module:

This is called after the translated model has been saved,
like :attr:`~django.db.models.signals.post_save`.

Arguments sent with this signal:

``sender``
    The model class.

``instance``
    The actual translated model instance being saved.

``raw``
    ``True`` when the model is being created by a fixture.

``using``
    The database alias being used


``pre_translation_delete``
--------------------------

.. data:: parler.signals.pre_translation_delete
   :module:

This is called before the translated model is deleted,
like :attr:`~django.db.models.signals.pre_delete`.

Arguments sent with this signal:

``sender``
    The model class.

``instance``
    The actual translated model instance being deleted.

``using``
    The database alias being used


``post_translation_delete``
---------------------------

.. data:: parler.signals.post_translation_delete
   :module:

This is called after the translated model has been deleted,
like :attr:`~django.db.models.signals.post_delete`.

Arguments sent with this signal:

``sender``
    The model class.

``instance``
    The actual translated model instance being deleted.

``using``
    The database alias being used
