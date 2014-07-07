.. image:: https://badge.fury.io/py/django-parler.png
  :target: http://badge.fury.io/py/django-parler
  :alt: PyPI version

.. image::  https://travis-ci.org/edoburu/django-parler.png?branch=master
  :target: http://travis-ci.org/edoburu/django-parler
  :alt: build-status

.. image:: https://coveralls.io/repos/edoburu/django-parler/badge.png?branch=master
  :target: https://coveralls.io/r/edoburu/django-parler
  :alt: coverage

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

Installation
============

First install the module, preferably in a virtual environment::

    git clone https://github.com/edoburu/django-parler.git
    cd django-parler
    pip install .

Configuration
-------------

Add the following settings::

    INSTALLED_APPS += (
        'parler',
    )


By default, the fallback language is the same as ``LANGUAGE_CODE``.
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
            'fallback': 'en',             # defaults to PARLER_DEFAULT_LANGUAGE_CODE
            'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
        }
    }

When using ``settings.SITE_ID`` which is a setting of the sites framework
(``django.contrib.sites``) the ``PARLER_LANGUAGES`` dict can contain
site specific settings and the special ``None`` key is no longer used::

    PARLER_LANGUAGES = {
        # Global site
        1: (
            {'code': 'en',},
            {'code': 'en-us',},
            {'code': 'it',},
            {'code': 'nl',},
        ),
        # US site
        2: (
            {'code': 'en-us',},
            {'code': 'en',},
        ),
        # IT site
        3: (
            {'code': 'it',},
            {'code': 'en',},
        ),
        # NL site
        3: (
            {'code': 'nl',},
            {'code': 'en',},
        ),
        'default': {
            'fallback': 'en',             # defaults to PARLER_DEFAULT_LANGUAGE_CODE
            'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
        }
    }


Basic example
-------------

Extend the model class::

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFields


    class MyModel(TranslatableModel):
        translations = TranslatedFields(
            title = models.CharField(_("Title"), max_length=200)
        )

        class Meta:
            verbose_name = _("MyModel")

        def __unicode__(self):
            return self.title

Now, the ``title`` field is translated.


Using translated fields
-----------------------

Translated fields can be accessed directly::

    >>> from django.utils import translation
    >>> translation.activate('en')

    >>> object = MyModel.objects.all()[0]
    >>> object.get_current_language()
    'en'
    >>> object.title
    u'cheese omelet'

    >>> object.set_current_language('fr')       # Only switches
    >>> object.title = "omelette du fromage"    # Translation is created on demand.
    >>> object.save()

When an attribute is not translated yet, the default language will be returned.
The default language is configured by the ``PARLER_DEFAULT_LANGUAGE_CODE``
or ``PARLER_DEFAULT_LANGUAGE_CODE['default']['fallback']`` setting.

The objects can be fetched in a specific language::

    >>> objects = MyModel.objects.language('fr').all()
    >>> objects[0].title
    u'omelette du fromage'


Filtering translated objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To restrict the queryset to translated objects only, the following methods are available:

* ``MyObject.objects.translated(*language_codes, **translated_fields)`` - return only objects with a translation of ``language_codes``.
* ``MyObject.objects.active_translations(language_code=None, **translated_fields)`` - return only objects for the current language (and fallback if this applies).

The ``active_translations()`` method also returns objects which are translated in the fallback language,
unless ``hide_untranslated = True`` is used in the ``PARLER_LANGUAGES`` setting.

If you have to query a language and translated attribute, query both in a single ``.filter()`` call::

    from parler.utils import get_active_language_choices

    MyObject.objects.filter(
        translations__language_code__in=get_active_language_choices(),
        translations__slug='omelette'
    )

For convenience, use the provided methods::

    MyObject.objects.translated(get_active_language_choices(), slug='omelette')

    MyObject.objects.active_translations(slug='omelette')

.. note::
   Due to Django ORM design, queries on the translated fields model should occur in a single ``.filter(..)`` or ``.translated(..)`` call.
   When using ``.filter(..).filter(..)``, the ORM turns that into 2 separate joins on the translations table.
   See `the ORM documentation <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_ for more details.


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


TODO
====

* ``ModelAdmin.prepopulated_fields`` doesn't work yet (you can use ``get_prepopulated_fields()`` as workaround).
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
.. _django-polymorphic: https://github.com/chrisglass/django_polymorphic
.. _documentation: http://django-parler.readthedocs.org/
