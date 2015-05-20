Changelog
=========

Changes in git
--------------

* Fix Django 1.4 support for using ``request.resolver_match``.
* Fix admin delete translation view when using ``prefetch_related('translations')`` by default in the managers ``get_queryset()`` method.
* Return to change view after deleting a translation.


Changes in version 1.4 (2015-04-13)
-----------------------------------

* Added Django 1.8 support
* Fix caching when using redis-cache
* Fix handling ``update_fields`` in ``save()`` (needed for combining parler with django-mptt_ 0.7)
* Fix unwanted migration changes in Django 1.6/South for the internal ``HideChoicesCharField``.
* Fix overriding get_current_language() / get_form_language() in the ``TranslatableModelFormMixin``/``TranslatableCreateView``/``TranslatableUpdateView``.


Changes in version 1.3 (2015-03-13)
-----------------------------------

* Added support for ``MyModel.objects.language(..).create(..)``.
* Detect when translatable fields are assigned too early.
* Fix adding ``choices=LANGUAGES`` to all Django 1.7 migrations.
* Fix missing 404 check in delete-translation view.
* Fix caching for models that have a string value as primary key.
* Fix support for a primary-key value of ``0``.
* Fix ``get_form_class()`` override check for ``TranslatableModelFormMixin`` for Python 3.
* Fix calling manager methods on related objects in Django 1.4/1.5.
* Improve ``{% get_translated_url %}``, using ``request.resolver_match`` value.
* Fix preserving query-string in ``{% get_translated_url %}``, unless an object is explicitly passed.
* Fix supporting removed model fields in ``get_cached_translation()``.


Changes in version 1.2.1 (2014-10-31)
-------------------------------------

* Fixed fetching correct translations when using ``prefetch_related()``.


Changes in version 1.2 (2014-10-30)
-----------------------------------

* Added support for translations on multiple model inheritance levels.
* Added ``TranslatableAdmin.get_translation_objects()`` API.
* Added ``TranslatableModel.create_translation()`` API.
* Added ``TranslatableModel.get_translation()`` API.
* Added ``TranslatableModel.get_available_languages(include_unsaved=True)`` API.
* **NOTE:** the ``TranslationDoesNotExist`` exception inherits from ``ObjectDoesNotExist`` now.
  Check your exception handlers when upgrading.


Changes in version 1.1.1 (2014-10-14)
-------------------------------------

* Fix accessing fields using ``safe_translation_getter(any_language=True)``
* Fix "dictionary changed size during iteration" in ``save_translations()`` in Python 3.
* Added ``default_permissions=()`` for translated models in Django 1.7.


Changes in version 1.1 (2014-09-29)
-----------------------------------

* Added Django 1.7 compatibility.
* Added ``SortedRelatedFieldListFilter`` for displaying translated models in the ``list_filter``.
* Added ``parler.widgets`` with ``SortedSelect`` and friends.
* Fix caching translations in Django 1.6.
* Fix checking ``unique_together`` on the translated model.
* Fix access to ``TranslatableModelForm._current_language`` in early ``__init__()`` code.
* Fix ``PARLER_LANGUAGES['default']['fallback']`` being overwritten by ``PARLER_DEFAULT_LANGUAGE_CODE``.
* Optimized prefetch usage, improves loading of translated models.
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
.. _django-mptt: https://github.com/django-mptt/django-mptt
.. _django-rest-framework: https://github.com/tomchristie/django-rest-framework
