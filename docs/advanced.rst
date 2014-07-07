Advanced usage patterns
=======================

Translations without fallback languages
---------------------------------------

When a translation is missing, the fallback language is used.
However, when an object has no fallback language, this still fails.

There are a few solutions to this problem:

1. Declare the translated attribute explicitly with ``any_language=True``::

        from parler.models import TranslatableModel
        from parler.fields import TranslatedField

        class MyModel(TranslatableModel):
            title = TranslatedField(any_language=True)

   Now, the title will try to fetch one of the existing languages from the database.

2. Use :func:`~parler.models.TranslatableModel.safe_translation_getter` on attributes
   which don't have an ``any_language=True`` setting. For example::

        model.safe_translation_getter("fieldname", any_language=True)

3. Catch the :class:`~parler.models.TranslationDoesNotExist` exception. For example::

        try:
            return object.title
        except TranslationDoesNotExist:
            return ''

   Because this exception inherits from :class:`~exceptions.AttributeError`,
   templates already display empty values by default.

4. Avoid fetching untranslated objects using queryset methods. For example::

        queryset.active_translations()

   Which is almost identical to::

        codes = get_active_language_choices()
        queryset.filter(translations__language_code__in=codes).distinct()

   Note that the same `ORM restrictions <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_ apply here.


Multi-site support
------------------

When using the sites framework (:mod:`django.contrib.sites`) and the :django:setting:`SITE_ID`
setting, the dict can contain entries for every site ID.
See the :ref:`configuration <multisite-configuration>` for more details.


Using translated slugs in views
-------------------------------

To handle translatable slugs in the :class:`~django.views.generic.detail.DetailView`,
the :class:`~parler.views.TranslatableSlugMixin` can be used to make this work smoothly.
For example::

.. code-block:: python

    class ArticleDetailView(TranslatableSlugMixin, DetailView):
        model = Article
        template_name = 'article/details.html'

The :class:`~parler.views.TranslatableSlugMixin` makes sure that:

* The object is fetched in the proper translation.
* The slug field is read from the translation model, instead of the shared model.
* Fallback languages are handled.
* Objects are not accidentally displayed in their fallback slug, but redirect to the translated slug.


Constructing the translations model manually
--------------------------------------------

It's also possible to create the translated fields model manually:

.. code-block:: python

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFieldsModel
    from parler.fields import TranslatedField


    class MyModel(TranslatableModel):
        title = TranslatedField()  # Optional, explicitly mention the field

        class Meta:
            verbose_name = _("MyModel")

        def __unicode__(self):
            return self.title


    class MyModelTranslation(TranslatedFieldsModel):
        master = models.ForeignKey(MyModel, related_name='translations', null=True)
        title = models.CharField(_("Title"), max_length=200)

        class Meta:
            verbose_name = _("MyModel translation")

This has the same effect, but also allows to to override
the :func:`~django.db.models.Model.save` method, or add new methods yourself.


Adding translated fields to an existing model
---------------------------------------------

Create a proxy class::

    from django.contrib.sites.models import Site
    from parler.models import TranslatableModel, TranslatedFields


    class TranslatableSite(TranslatableModel, Site):
        class Meta:
            proxy = True

        translations = TranslatedFields()


And update the admin::

    from django.contrib.sites.admin import SiteAdmin
    from django.contrib.sites.models import Site
    from parler.admin import TranslatableAdmin, TranslatableStackedInline


    class NewSiteAdmin(TranslatableAdmin, SiteAdmin):
        pass

    admin.site.unregister(Site)
    admin.site.register(TranslatableSite, NewSiteAdmin)


Disabling caching
-----------------

If desired, caching of translated fields can be disabled
by adding :ref:`PARLER_ENABLE_CACHING = False <PARLER_ENABLE_CACHING>` to the settings.

.. _custom-language-settings:

Customizing language settings
-----------------------------

If needed, projects can "fork" the parler language settings.
This is rarely needed. Example::

    from django.conf import settings
    from parler import appsettings as parler_appsettings
    from parler.utils import normalize_language_code, is_supported_django_language
    from parler.utils.conf import add_default_language_settings

    MYCMS_DEFAULT_LANGUAGE_CODE = getattr(settings, 'MYCMS_DEFAULT_LANGUAGE_CODE', FLUENT_DEFAULT_LANGUAGE_CODE)
    MYCMS_LANGUAGES = getattr(settings, 'MYCMS_LANGUAGES', parler_appsettings.PARLER_LANGUAGES)

    MYCMS_DEFAULT_LANGUAGE_CODE = normalize_language_code(MYCMS_DEFAULT_LANGUAGE_CODE)

    MYCMS_LANGUAGES = add_default_language_settings(
        MYCMS_LANGUAGES, 'MYCMS_LANGUAGES',
        hide_untranslated=False,
        hide_untranslated_menu_items=False,
        code=MYCMS_DEFAULT_LANGUAGE_CODE,
        fallback=MYCMS_DEFAULT_LANGUAGE_CODE
    )

Instead of using the functions from :mod:`parler.utils` (such as :func:`~parler.utils.get_active_language_choices`)
the project can access the language settings using::

    MYCMS_LANGUAGES.get_language()
    MYCMS_LANGUAGES.get_active_choices()
    MYCMS_LANGUAGES.get_fallback_language()
    MYCMS_LANGUAGES.get_default_language()
    MYCMS_LANGUAGES.get_first_language()

These methods are added by the :func:`~parler.utils.conf.add_default_language_settings` function.
See the :class:`~parler.utils.conf.LanguagesSetting` class for details.
