Using multiple databases
========================

.. versionchanged:: 2.x
    In previous versions, the caching mechanism was common to all databases with nasty side-effects when using the same model in several databases.

Overview
--------

When using multiple databases, we expect the behaviour of translatable models to be as close as possible to the behaviour of plain models, when performing similar operations.

Saving a new model to a non-default database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We expect to be able to save a newly created model instance in any (properly configured) database, and we expect subsequent database operations to be performed in the same database by default. This is the standard behaviour for models, and is indeed honored by translatable models:

.. code-block:: python

        obj = MyModel(...)
        obj.save(using="my_db")
        # modify obj
        obj.save()   # Saves in my_db implicitly.

Retrieving a model from a non-default database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When retrieving a model from a non-default database (e.g with ``MyModel.objects.using("my_db").filter(...)``), we expect a subsequent call to ``my_instance.save()`` or ``my_instance.delete()`` (without an explicit ``using="my_db"`` argument) to be applied in the database the instance was retrieved from, and we expect *all* translations to be saved or deleted, together with the master model instance.  This is the standard behaviour for models, and is indeed honored by translatable models:

.. code-block:: python

    obj = MyModel.objects.using("my_db").get(....)
    # modify obj
    obj.save()   # Saves in my_db implicitly.

Duplicating a model retrieved from a database into another database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::
    Translatable models do not support duplicating a model into another database through the :func:`~parle.model.TranslatableModel.save` method.

When working with a model created in ``'my_db'`` or retrieved from ``'my_db'``, we would expect to be able to save it in another database, like we do with plain models: set the primary key to None and call ``save(using=my_other_db")``.  **This is not how django-parler works**.

Attempting a duplication using the :func:`~parle.model.TranslatableModel.save` method raises a ``ProgrammingError`` exception.

.. code-block:: python

    obj = MyModel(...)
    obj.save(using="my_db")
    # or obj = MyModel.objects.using("my_db").get(....)
    # modify obj
    obj.pk = None  # to force insertion of a new model, not update of an existing one which would
                   # happen to have the same primary-key.
    obj.save(using="my_other_db")   # Would work with a plain model, but WILL RAISE A
                                    # ProgrammingError FOR A TRANSLATABLE MODEL

.. code-block:: python

    obj = MyModel(...)  # or obj = MyModel.objects.using("my_db").get(....)
    # Possibly update obj but keep a pk value which is not None, in an attempt to update the
    # model with this pk in my_other_db
    obj.save(using="my_other_db")   # Would work with a plain model, but WILL RAISE A
                                    # ProgrammingError FOR A TRANSLATABLE MODEL

To save a model from one database to another, use the dedicated methods ``duplicate_into(db_alias:str)`` **without altering the primary key**, which will:

* Upload all existing unchanged translations from the original database

* Create the model in the new database, along with all translations, including the new translations or changes which were not committed to the original database.

NB: Unsaved changed are **not** committed to the original database.

.. code-block:: python

    obj = MyModel.objects.using("my_db").get(....)
    # possibly modify obj
    obj.my_attribute = "xyz"
    obj.duplicate_into("my_other_db")  # save the model as modified, along with all existing
                                       # translations as a new model into the new db, assigning new
                                       # primary keys.
    # further use the object which is the one in "my_other_db"
    obj.my_other_attribute = "abc"
    obj.save()                         # saves in "my_other_db"

For the technical reasons behind this design, see :doc:`this page <multiple_db_design>`.
