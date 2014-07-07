.. _quickstart:

Quick start guide
=================

Installing django-parler
------------------------

The package can be installed using::

    pip install django-parler

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
The translated fields can be accessed directly::

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

When fetching objects, the :func:`~parler.managers.TranslatableManager.language` method
can be used to configure the active language of the returned objects.
By default, the current Django language is used.

    >>> objects = MyModel.objects.language('fr').all()
    >>> objects[0].title
    u'omelette du fromage'

When an attribute is not translated yet, the default language
(set by :ref:`PARLER_DEFAULT_LANGUAGE_CODE` or ``PARLER_DEFAULT_LANGUAGE_CODE['default']['fallback']``)
will be returned.


Querying translated attributes
------------------------------

To restrict the queryset to translated objects only, the following methods are available:

* :func:`MyObject.objects.translated(*language_codes, **translated_fields) <parler.managers.TranslatableManager.translated>` - return only objects with a translation of ``language_codes``.
* :func:`MyObject.objects.active_translations(language_code=None, **translated_fields) <parler.managers.TranslatableManager.active_translations` - return only objects for the current language (and fallback if this applies).

The :func:`parler.managers.TranslatableManager.active_translations` method also returns objects which are translated in the fallback language,
unless ``hide_untranslated = True`` is used in the :ref:`PARLER_LANGUAGES`` setting.

.. note::
   These methods perform a query on the ``translations__language_code`` field.
   Hence, they can't be combined with other filters on translated fields,
   as that causes double joins on the translations table.
   See `the ORM documentation <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_ for more details.

Advanced
~~~~~~~~

The translated fields can also be filtered like any normal relation::

    object = MyObject.objects.filter(translations__title='omelette')

    translation1 = myobject.translations.all()[0]

If you have to query a language and translated attribute,
both should be queried in a single ``.filter()`` call::

    from parler.utils import get_active_language_choices

    MyObject.objects.filter(
        translations__language_code__in=get_active_language_choices(),
        translations__slug='omelette'
    )

For convenience, use the provided methods::

* :func:`MyObject.objects.translated(get_active_language_choices(), slug='omelette') <parler.managers.TranslatableManager.translated>`
* :func:`MyObject.objects.active_translations(slug='omelette') <parler.managers.TranslatableManager.active_translations>`

.. note::

    Due to the Django ORM design, the query for translated attributes should
    typically occur within a single ``.filter(..)`` call. When using ``.filter(..).filter(..)``,
    the ORM turns that into 2 separate joins on the translations table.
    See `the ORM documentation <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_ for more details.

