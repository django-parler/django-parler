.. _quickstart:

Quick start guide
=================

Installing django-parler
------------------------

The package can be installed using::

    pip install django-parler

Add the following settings::

    INSTALLED_APPS += (
        'parler',
    )


A brief overview
----------------

Creating models
~~~~~~~~~~~~~~~

Using the :class:`~parler.models.TranslatedFields` wrapper, model fields can be marked as translatable::

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFields

    class MyModel(TranslatableModel):
        translations = TranslatedFields(
            title = models.CharField(_("Title"), max_length=200)
        )

        def __unicode__(self):
            return self.title

Accessing fields
~~~~~~~~~~~~~~~~

Translatable fields can be used like regular fields::

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
~~~~~~~~~~~~~~~~~~~~~~

To query translated fields, use the :func:`~parler.managers.TranslatableManager.translated` method::

    MyObject.objects.translated(title='cheese omelet')

To access objects in both the current and the configured fallback languages, use::

    MyObject.objects.active_translations(title='cheese omelet')

This returns objects in the languages which are considered "active", which are:

* The current language
* The fallback languages when ``hide_untranslated=False`` in the :ref:`PARLER_LANGUAGES` setting.

.. note::

   Due to :ref:`ORM restrictions <orm-restrictions>` the query should be performed in
   a single :func:`~parler.managers.TranslatableManager.translated`
   or :func:`~parler.managers.TranslatableManager.active_translations` call.

   The :func:`~parler.managers.TranslatableManager.active_translations` method typically needs to
   include a :func:`~django.db.models.query.QuerySet.distinct` call to avoid duplicate results of the same object.


Changing the language
~~~~~~~~~~~~~~~~~~~~~

The queryset can be instructed to return objects in a specific language::

    >>> objects = MyModel.objects.language('fr').all()
    >>> objects[0].title
    u'omelette du fromage'

This only sets the language of the object.
By default, the current Django language is used.

Use :func:`~parler.models.TranslatableModel.get_current_language`
and :func:`~parler.models.TranslatableModel.set_current_language`
to change the language on individual objects.
There is a context manager to do this temporary::

    from parler.utils.context import switch_language

    with switch_language(model, 'fr'):
        print model.title

And a function to query just a specific field::

    model.safe_translation_getter('title', language_code='fr')


Configuration
-------------

By default, the fallback languages are the same as: ``[LANGUAGE_CODE]``.
The fallback language can be changed in the settings::

    PARLER_DEFAULT_LANGUAGE_CODE = 'en'


Optionally, the admin tabs can be configured too::

    PARLER_LANGUAGES = {
        None: (
            {'code': 'en',},
            {'code': 'en-us',},
            {'code': 'it',},
            {'code': 'nl',},
        ),
        'default': {
            'fallbacks': ['en'],          # defaults to PARLER_DEFAULT_LANGUAGE_CODE
            'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
        }
    }

Replace ``None`` with the ::setting:`SITE_ID` when you run a multi-site project with the sites framework.
Each ::setting:`SITE_ID` can be added as additional entry in the dictionary.
