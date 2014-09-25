Changelog
=========

Changes in version 1.1 (in development)
---------------------------------------

* Added ``SortedRelatedFieldListFilter`` for displaying translated models in the ``list_filter``.
* Added ``parler.widgets`` with ``SortedSelect`` and friends.
* Added Django 1.7 compatibility.
* Fix checking ``unique_together`` on the translated model.
* Fix storing cached translations in Django 1.6.
* Fix access to ``TranslatableModelForm._current_language`` in early ``__init__()`` code.
* **BACKWARDS INCOMPATIBLE:** The arguments of ``get_cached_translated_field()`` have changed ordering, ``field_name`` comes before ``language_code`` now.


Changes in version 1.0 (2014-07-07)
-----------------------------------

Released in 1.0b3:
~~~~~~~~~~~~~~~~~~

* Added ``TranslatableSlugMixin``, to be used for detail views.
* Fixed translated field names in admin ``list_display``, added ``short_description`` to ``TranslatedFieldDescriptor``
* Fix internal server errors in ``{% get_translated_url %}`` for function-based views with class kwargs
* Improved admin layout for ``save_on_top=True``.


Released in 1.0b2:
~~~~~~~~~~~~~~~~~~

* Fixed missing app_label in cache key, fixes support for multiple models with the same name.
* Fixed "dictionary changed size during iteration" in ``save_translations()``


Released in 1.0b1:
~~~~~~~~~~~~~~~~~~

* Added ``get_translated_url`` template tag, to implement language switching easily.
  This also allows to implement `hreflang <https://support.google.com/webmasters/answer/189077>`_ support for search engines.
* Added a ``ViewUrlMixin`` so views can tell the template what their exact canonical URL should be.
* Added ``TranslatableCreateView`` and ``TranslatableUpdateView`` views, and associated mixins.
* Fix missing "language" GET parmeter for Django 1.6 when filtering in the admin (due to the ``_changelist_filters`` parameter).
* Support missing `SITE_ID` setting for Django 1.6.


Released in 1.0a1:
~~~~~~~~~~~~~~~~~~

* **BACKWARDS INCOMPATIBLE:** updated the model name of the dynamically generated translation models for django-hvad_ compatibility.
  This only affects your South migrations. Use ``manage.py schemamigration appname --empty "upgrade_to_django_parler10"`` to upgrade
  applications which use ``translations = TranslatedFields(..)`` in their models.
* Added Python 3 compatibility!
* Added support for ``.prefetch('translations')``.
* Added automatic caching of translated objects, use ``PARLER_ENABLE_CACHING = False`` to disable.
* Added inline tabs support (if the parent object is not translatable).
* Allow ``.translated()`` and ``.active_translations()`` to filter on translated fields too.
* Added ``language_code`` parameter to ``safe_translation_getter()``, to fetch a single field in a different language.
* Added ``switch_language()`` context manager.
* Added ``get_fallback_language()`` to result of ``add_default_language_settings()`` function.
* Added partial support for tabs on inlines when the parent object isn't a translated model.
* Make settings.SITE_ID setting optional
* Fix inefficient or unneeded queries, i.e. for new objects.
* Fix supporting different database (using=) arguments.
* Fix list language, always show translated values.
* Fix ``is_supported_django_language()`` to support dashes too
* Fix ignored ``Meta.fields`` declaration on forms to exclude all other fields.


Changes in version 0.9.4 (beta)
-------------------------------

* Added support for inlines!
* Fix error in Django 1.4 with "Save and continue" button on add view.
* Fix error in ``save_translations()`` when objects fetched fallback languages.
* Add ``save_translation(translation)`` method, to easily hook into the ``translation.save()`` call.
* Added support for empty ``translations = TranslatedFields()`` declaration.


Changes in version 0.9.3 (beta)
-------------------------------

* Support using ``TranslatedFieldsModel`` with abstract models.
* Added ``parler.appsettings.add_default_language_settings()`` function.
* Added ``TranslatableManager.queryset_class`` attribute to easily customize the queryset class.
* Added ``TranslatableManager.translated()`` method to filter models with a specific translation.
* Added ``TranslatableManager.active_translations()`` method to filter models which should be displayed.
* Added ``TranslatableAdmin.get_form_language()`` to access the currently active language.
* Added ``hide_untranslated`` option to the ``PARLER_LANGUAGES`` setting.
* Added support for ``ModelAdmin.formfield_overrides``.


Changes in version 0.9.2 (beta)
-------------------------------

* Added ``TranslatedField(any_language=True)`` option, which uses any language as fallback
  in case the currently active language is not available. This is ideally suited for object titles.
* Improved ``TranslationDoesNotExist`` exception, now inherits from ``AttributeError``.
  This missing translations fail silently in templates (e.g. admin list template)..
* Added unittests
* Fixed Django 1.4 compatibility
* Fixed saving all translations, not only the active one.
* Fix sending ``pre_translation_save`` signal.
* Fix passing ``_current_language`` to the model __init__ function.


Changes in version 0.9.1 (beta)
-------------------------------

* Added signals to detect translation model init/save/delete operations.
* Added default ``TranslatedFieldsModel`` ``verbose_name``, to improve the delete view.
* Allow using the ``TranslatableAdmin`` for non-``TranslatableModel`` objects (operate as NO-OP).


Changes in version 0.9 (beta)
-----------------------------

* First version, based on intermediate work in django-fluent-pages_.
  Integrating django-hvad_ turned out to be very complex, hence this app was developped instead.


.. _django-fluent-pages: https://github.com/edoburu/django-fluent-pages
.. _django-hvad: https://github.com/kristianoellegaard/django-hvad
