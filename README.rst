.. image:: https://img.shields.io/travis/django-parler/django-parler/master.svg?branch=master
    :target: http://travis-ci.org/django-parler/django-parler
.. image:: https://readthedocs.org/projects/django-parler/badge/?version=stable
    :target: https://django-parler.readthedocs.io/en/stable/
.. image:: https://img.shields.io/pypi/v/django-parler.svg
    :target: https://pypi.python.org/pypi/django-parler/
.. image:: https://img.shields.io/pypi/l/django-parler.svg
    :target: https://pypi.python.org/pypi/django-parler/
.. image:: https://img.shields.io/codecov/c/github/django-parler/django-parler/master.svg
    :target: https://codecov.io/github/django-parler/django-parler?branch=master

django-parler
=============

Simple Django model translations without nasty hacks.

Features:

* Nice admin integration.
* Access translated attributes like regular attributes.
* Automatic fallback to the default language.
* Separate table for translated fields, compatible with django-hvad_.
* Plays nice with others, compatible with django-polymorphic_, django-mptt_ and such:

  * No ORM query hacks.
  * Easy to combine with custom Manager or QuerySet classes.
  * Easy to construct the translations model manually when needed.

See the documentation_ for more details.


A brief overview
================

Installing django-parler
------------------------

The package can be installed using:

.. code-block:: bash

    pip install django-parler

Add the following settings:

.. code-block:: python

    INSTALLED_APPS += (
        'parler',
    )

Optionally, the admin tabs can be configured too:

.. code-block:: python

    PARLER_LANGUAGES = {
        None: (
            {'code': 'en',},
            {'code': 'en-us',},
            {'code': 'it',},
            {'code': 'nl',},
        ),
        'default': {
            'fallback': 'en',             # defaults to PARLER_DEFAULT_LANGUAGE_CODE
            'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
        }
    }

Replace ``None`` with the ``SITE_ID`` when you run a multi-site project with the sites framework.
Each ``SITE_ID`` can be added as additional entry in the dictionary.

Make sure your project is configured for multiple languages.
It might be useful to limit the ``LANGUAGES`` setting. For example:

.. code-block:: python

    from django.utils.translation import gettext_lazy as _

    LANGUAGE_CODE = 'en'

    LANGUAGES = (
        ('en', _("English")),
        ('en-us', _("US English")),
        ('it', _('Italian')),
        ('nl', _('Dutch')),
        ('fr', _('French')),
        ('es', _('Spanish')),
    )

By default, the fallback language is the same as ``LANGUAGE_CODE``.
The fallback language can be changed in the settings:

.. code-block:: python

    PARLER_DEFAULT_LANGUAGE_CODE = 'en'


Creating models
---------------

Using the ``TranslatedFields`` wrapper, model fields can be marked as translatable:

.. code-block:: python

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFields

    class MyModel(TranslatableModel):
        translations = TranslatedFields(
            title = models.CharField(_("Title"), max_length=200)
        )

        def __unicode__(self):
            return self.title

Accessing fields
----------------

Translatable fields can be used like regular fields:

.. code-block:: python

    >>> object = MyModel.objects.all()[0]
    >>> object.get_current_language()
    'en'
    >>> object.title
    u'cheese omelet'

    >>> object.set_current_language('fr')       # Only switches
    >>> object.title = "omelette du fromage"    # Translation is created on demand.
    >>> object.save()

Internally, django-parler stores the translated fields in a separate model, with one row per language.

Filtering translations
----------------------

To query translated fields, use the ``.translated()`` method:

.. code-block:: python

    MyObject.objects.translated(title='cheese omelet')

To access objects in both the current and possibly the fallback language, use:

.. code-block:: python

    MyObject.objects.active_translations(title='cheese omelet')

This returns objects in the languages which are considered "active", which are:

* The current language
* The fallback language when ``hide_untranslated=False`` in the ``PARLER_LANGUAGES`` setting.


Changing the language
---------------------

The queryset can be instructed to return objects in a specific language:

.. code-block:: python

    >>> objects = MyModel.objects.language('fr').all()
    >>> objects[0].title
    u'omelette du fromage'

This only sets the language of the object.
By default, the current Django language is used.

Use ``object.get_current_language()`` and ``object.set_current_language()``
to change the language on individual objects.
There is a context manager to do this temporary:

.. code-block:: python

    from parler.utils.context import switch_language

    with switch_language(model, 'fr'):
        print model.title

And a function to query just a specific field:

.. code-block:: python

    model.safe_translation_getter('title', language_code='fr')


Advanced Features
-----------------

This package also includes:

* Creating the ``TranslatedFieldsModel`` manually!
* Form classes for inline support.
* View classes for switching languages, creating/updating translatable objects.
* Template tags for language switching-buttons.
* ORM methods to handle the translated fields.
* Admin inlines support.

See the documentation_ for more details.


Special notes
=============

* Using ``ModelAdmin.prepopulated_fields`` doesn't work, but you can use ``get_prepopulated_fields()`` as workaround.
* Due to `ORM restrictions <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_
  queries for translated fields should be performed in a single ``.translated(..)`` or ``.active_translations(..)`` call.
* The ``.active_translations(..)`` method typically needs to ``.distinct()`` call to avoid duplicate results of the same object.


TODO
====

* The list code currently performs one query per object. This needs to be reduced.
* Preferably, the ``TranslatedField`` proxy on the model should behave like a ``RelatedField``,
  if that would nicely with the ORM too.

Please contribute your improvements or work on these area's!


Contributing
============

This module is designed to be generic. In case there is anything you didn't like about it,
or think it's not flexible enough, please let us know. We'd love to improve it!

If you have any other valuable contribution, suggestion or idea,
please let us know as well because we will look into it.
Pull requests are welcome too. :-)


.. _django-hvad: https://github.com/kristianoellegaard/django-hvad
.. _django-mptt: https://github.com/django-mptt/django-mptt
.. _django-fluent-pages: https://github.com/edoburu/django-fluent-pages
.. _django-polymorphic: https://github.com/django-polymorphic/django-polymorphic
.. _documentation: https://django-parler.readthedocs.io/
