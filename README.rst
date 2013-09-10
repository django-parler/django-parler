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
            'fallback': 'en',  # defaults to PARLER_DEFAULT_LANGUAGE_CODE
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

    >>> objects = MyModel.objects.language('fr').all()
    >>> objects[0].title
    u'omelette du fromage'

When an attribute is not translated yet, the default language
(set by ``PARLER_DEFAULT_LANGUAGE_CODE`` or ``PARLER_DEFAULT_LANGUAGE_CODE['default']['fallback']``)
will be retured.


Querying translated attributes
------------------------------

Currently, this package doesn't improve the QuerySet API to access translated fields.
Hence, simply access the translated fields like any normal relation::

    object = MyObject.objects.filter(translations__title='omelette')

    translation1 = myobject.translations.all()[0]

Note that due to the Django ORM design, the query for translated attributes should
typically occur within a single ``.filter(..)`` call. When using ``.filter(..).filter(..)``,
the ORM turns that into 2 separate joins on the translations table.
See `the ORM documentation <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_ for more details.


Advanced example
----------------

The translated model can be constructed manually too::

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFieldsModel
    from parler.managers import TranslatedManager
    from parler.fields import TranslatedField


    class MyModel(TranslatableModel):
        title = TranslatedField()  # Optional, explicitly mention the field

        objects = TranslatedManager()

        class Meta:
            verbose_name = _("MyModel")

        def __unicode__(self):
            return self.title


    class MyModel_Translations(TranslatedFieldsModel):
        master = models.ForeignKey(MyModel, related_name='translations', null=True)
        title = models.CharField(_("Title"), max_length=200)

        class Meta:
            verbose_name = _("MyModel translation")


Background story
================

This package is inspired by django-hvad_. When attempting to integrate multilingual
support into django-fluent-pages_ using django-hvad_ this turned out to be really hard.
The sad truth is that while django-hvad_ has a nice admin interface, table layout and model API,
it also overrides much of the default behavior of querysets and model metaclasses.
Currently, this prevents combining django-hvad_ with django-polymorphic_.

When investigating other multilingual packages, they either appeared to be outdated,
store translations in the same table (too inflexible for us) or only provided a model API.
Hence, there was a need for a new solution, using a simple, crude but effective API.

Initially, multilingual support was coded directly within django-fluent-pages_,
while keeping a future django-hvad_ transition in mind. Instead of doing metaclass operations,
the "shared model" just proxied all attributes to the translated model (all manually constructed).
Queries just had to be performed using ``.filter(translations__title=..)``.
This proved to be a sane solution and quickly it turned out that this code
deserved a separate package, and some other modules needed it too.

This package is an attempt to combine the best of both worlds;
the API simplicity of django-hvad_ with the crude,
but effective solution of proxying translated attributes.
And yes, we've added some metaclass magic too - to make life easier -
without loosing the freedom of manually using the API at your will.

TODO
----

* Unittests and documentation on RTD.
* ``ModelAdmin.prepopulated_fields`` doesn't work yet (you can use ``get_prepopulated_fields()`` as workaround).
* The admin forms use the standard form widgets instead of the admin overrides.
* The list code currently performs one query per object. This needs to be reduced.
* Preferably, the ``TranslatedField`` proxy on the model should behave like a ``RelatedField``,
  if that would nicely with the ORM too.


API
====

On ``parler.models.TranslatableModel``:

* ``get_current_language()``
* ``set_current_language(language_code, initialize=False)``
* ``get_available_languages()``
* ``has_translation(language_code=None)``
* ``save_translations()``

On ``parler.models.TranslatedFieldsModel``:

* ``language_code`` - The language code field.
* ``master`` - ForeignKey to the shared table.
* ``is_modified`` - Property to detect changes.
* ``get_translated_fields()`` - The names of translated fields.

On ``parler.managers.TranslatedManager``:

* ``language(language_code=None)`` - set the language of returned objects.

In ``parler.utils``:

* ``normalize_language_code()``
* ``is_supported_django_language()``
* ``get_language_title()``
* ``get_language_settings()``
* ``is_multilingual_project()``


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
