Duplicating instances, using multiple databases and more...
===========================================================

.. versionchanged:: 2.x
    In previous versions, the caching mechanism was common to all databases with nasty side-effects when managing instances of the same Model in several databases. Once fixed, tests revealed that a number of operations commonly performed on plain Models where either silently failing or resulting in unintuitive effects (compared to the effects described by Django documentation about plain Models. Hence this summary to clarify how typical Django operation are supported for translatable models.

Overview
--------

When using single or multiple databases, we expect the behaviour of translatable models to be as close as possible to the behaviour of plain models (as described in Django documentation), when performing similar operations. This page reviews the main operations we can perform on Models, and clarifies how Django-parler provides the same behaviour for translatable models.

.. note:: Django documentation (https://docs.djangoproject.com/en/4.2/topics/db/multi-db/) states that

        "If you don’t specify using, the save() method will save into the default database allocated by the routers."

    and

        "By default, a call to delete an existing object will be executed on the same database that was used to retrieve the object in the first place."

    After careful checking and testing: delete() and save() BOTH determine the database to use the same way,
    and both use as default db, the database from which the object was retrieved. The statement above about ``save()`` is only valid if the object was never saved into a database before.


Creating a new model
--------------------

The typical creation of a regular model is:

.. code-block:: python

    obj = MyModel(...)
    # set here any number of attribute and/or relations
    obj.save()  # or obj.save(using="my_db")

The corresponding sequence for a translatable model is:

.. code-block:: python

    obj = MyTranslatableModel(...)
    # set here any number of attribute and/or relations in any number of languages
    obj.save()  # or obj.save(using="my_db")

The sequence is strictly similar, and Django-parler saves all translations, just as Django ORM saves all fields. In both cases, if the instance is saved to a non-default database ``my_db`` (with ``save(using="my_db")``), any further operation will by default be performed on ``my_db``.

Retrieving a model from a non-default database
----------------------------------------------

When retrieving a model from a non-default database (e.g with ``MyModel.objects.using("my_db").filter(...)``), we expect a subsequent database operation (e.g ``my_instance.save()`` or ``my_instance.delete()``, without an explicit ``using="my_db"`` argument) to be applied to the database the instance was retrieved from, and we expect *all* translations to be saved or deleted, together with the master model instance.  This is the standard behaviour for regular models, and is similarly implemented by translatable models:

.. code-block:: python

    obj = MyTranslatableModel.objects.using("my_db").get(....)
    # modify instance and translations in any language
    obj.save()   # Saves all translations in my_db implicitly.

Duplicating a model retrieved from a database into the same or another database
-------------------------------------------------------------------------------

.. versionchanged 2.x :: Version <= 2.3 did not save non-prefetched translations nor unchanged translations when duplicating a translatable model.

When working with a model created in ``'my_db'`` or retrieved from ``'my_db'``, a plain model allows to
easily insert it in another database or duplicate it in the same database:

.. code-block:: python

    obj = MyModel.objects.get(....)
    # possibly modify obj
    obj.pk = None
    obj.save()  #  or obj.save(using="another_db")

Translatable models behave the same way, saving all translations, including possible unsaved edits into the destination database. This enforces the principle that saving a translatable models saves **all** translations.

.. code-block:: python

    obj = MyTranslatableModel.objects.get(....)
    # possibly modify obj and translations in any language
    obj.pk = None
    obj.save()  #  or obj.save(using="another_db") This saves all translations, including edits.

.. warning:: Unsaved changes to the original model are saved in the duplicate in the target database, but are **NOT** saved in the original model in the original database.

.. warning:: As for any Model, when duplicating to a new database, relations to other Models must be carefully considered. Django-parler takes care of transparently duplicating the translations as required, but any other foreign key in your model must be carefully managed to avoid inadvertently referencing models using foreign keys which only make sense in the original database.

Updating a model in another database by setting the primary key before saving
-----------------------------------------------------------------------------

Regular models allow this possibly dangerous (and mostly not advisable operation): if ``my_other_db`` includes a model with pk=123, we can force the pk of any model (previously saved in another database or not) to this value, and save it to ``my_other_db`` in order to **overwrite** the existing model (Django will in this case perform and ``UPDATE`` instead of an ``INSERT``). This operation is OK with a model without any relation to other models, but becomes very tricky if relations to other models must be managed.

.. code-block:: python

    obj = MyModel(...)  # or obj = MyModel.objects.using("my_db").get(....)
    # Possibly update obj
    obj.pk = 123    # set pk to the pk of an existing model in destination db to update the
                    # model with this pk in my_other_db
    obj.save(using="my_other_db")   # OK with a plain (simple) Model, NOT supported for translatable models.

Although possible, this operation requires some precautions to properly overwrite a translatable model: in the most general case, some translations must be overwritten (either with unsaved data or data from the database), some must be created (either with unsaved data or data from the database) and some must be deleted. This is currently NOT supported by django-parler. Attempting it raises a ``NomImplementedError``.

The construct is nevertheless accepted if no model with the provided primary key exists in the target database (and is then just a way to control the primary key of a newly created master model.

.. note:: Overwriting an existing model can usually as easily be achieved by retrieving the model from the database, updating it and saving it back.
