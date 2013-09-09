django-parler
=============

Simple Django model translations without nasty hacks, featuring nice admin integration.


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

    PARLER_DEFAULT_LANGUAGE_CODE = 'en'

    # Languages are configured per site-id
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
            'fallback': 'en',
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


API
---

On ``parler.models.TranslatableModel``:

* ``get_current_language()``
* ``set_current_language(language_code, initialize=False)``
* ``get_available_languages()``
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
------------

This module is designed to be generic. In case there is anything you didn't like about it,
or think it's not flexible enough, please let us know. We'd love to improve it!

If you have any other valuable contribution, suggestion or idea,
please let us know as well because we will look into it.
Pull requests are welcome too. :-)
