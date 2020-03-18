Changelog
=========

Changes in 2.0.1 (2020-01-02)
-----------------------------

* Fixed Django 3.0 compatibility by removing django.utils.six dependency.
* Fixed using ``value_from_object()`` instead of ``get_prep_value()`` in model forms initial data.
* Fixed using proper ``get_language()`` call when ``PARLER_DEFAULT_ACTIVATE`` is used.
* Fixed confusing ``AttributeError`` on ``_parler_meta`` when migrations don't inherit from ``TranslatableModel``.
* Added PARLER_CACHE_PREFIX for sites that share the same cache.


Changes in 2.0 (2019-07-26)
---------------------------

* Added Django 2.1 and 2.2 support
* Added translation support to data migrations.
* Fixed formatting of initial form values for translated fields.
* Fixed admin change view redirects to preserve ``?language=..`` in the query string.
* Fixed admin loading ``prepopulate.js`` for DEBUG=True.
* Fixed admin quoting for ``object_id`` URLs.
* Fixed ``UUIDField`` support.
* Fixed object creation when setting the ``pk`` field on newly added objects.
* Fixed check on ``MISSING`` sentinel when loading cached models.
* Fixed ``QuerySet._clone()`` argument signature.
* Fixed ``model.delete()`` call to return collector data.
* Fixed ``model.refresh_from_db()`` to clear the translations cache too.
* Fixed returning full full ``ValidationError`` data from ``validate_unique()``.
* Drop Django 1.7, 1.8, 1.9, 1.10 compatibility.


Changes in 1.9.2 (2018-02-12)
-----------------------------

* Fixed Django 2.0 ``contribute_to_class()`` call signature.
* Fixed "Save and add another" button redirect when using different admin sites.
* Fixed import location of ``mark_safe()``.


Changes in 1.9.1 (2017-12-06)
-----------------------------

* Fixed HTML output in Django 2.0 for the the ``language_column`` and ``all_languages_column`` fields in the Django admin.


Changes in 1.9 (2017-12-04)
---------------------------

* Added Django 2.0 support.
* Fixed ``get_or_create()`` call when no defaults are given.


Changes in 1.8.1 (2017-11-20)
-----------------------------

* Fixed checkes for missing fallback languages (``IsMissing`` sentinel value leaked through caching)
* Fixed preserving the language tab in the admin.
* Fixed ``get_or_create()`` call.


Changes in 1.8 (2017-06-20)
-----------------------------

* Dropped Django 1.5, 1.6 and Python 2.6 support.
* Fixed Django 1.10 / 1.11 support:

  * Fix ``.language('xx').get()`` usage.
  * Fix models construction via ``Model(**kwargs)``.
  * Fix test warnings due to tests corrupting the app registry.

* Fix support for ``ModelFormMixin.fields`` in ``TranslatableUpdateView``.
  Django allows that attribute as alternative to setting a ``form_class`` manually.


Changes in 1.7 (2016-11-29)
---------------------------

* Added ``delete_translation()`` API.
* Added ``PARLER_DEFAULT_ACTIVATE`` setting, which allows to display translated texts in the default
  language even through ``translation.activate()`` is not called yet.
* Improve language code validation in forms, allows to enter a language variant.
* Fixed not creating translations when default values were filled in.
* Fixed breadcrumb errors in delete translation view when using django-polymorphic-tree_.


Changes in 1.6.5 (2016-07-11)
-----------------------------

* Fix ``get_translated_url()`` when Django uses bytestrings for ``QUERY_STRING``.
* Raise ``ValidError`` when a ``TranslatableForm`` is initialized with a language code
  that is not available in ``LANGUAGES``.

**Backwards compatibility note:** An ``ValueError`` is now raised when forms are initialized
with an invalid languae code. If your project relied on invalid language settings, make sure
that ``LANGAUGE_CODE`` and ``LANGUAGES`` are properly configured.

Rationale: Since the security fix in v1.6.3 (to call the ``clean()`` method of translated fields),
invalid language codes are no longer accepted. The choice was either to passively warn and exclude
the language from validation checks, or to raise an error beforehand that the form is used
to initialize bad data. It's considered more important to avoid polluted database contents
then preserving compatibility, hence this check remains as strict.


Changes in 1.6.4 (2016-06-14)
-----------------------------

* Fix calling ``clean()`` on fields that are not part of the form.
* Fix tab appearance for Django 1.9 and flat theme.
* Fix issues with ``__proxy__`` field for template names
* Fix attempting to save invalid ``None`` language when Django translations are not yet initialized.

**Note:** django-parler models now mandate that a language code is selected; either by calling
``model.set_current_language()``, ``Model.objects.language()`` or activating a gettext environment.
The latter always happens in a standard web request, but needs to happen explicitly in management commands.
This avoids hard to debug situations where unwanted model changes happen on implicitly selected languages.


Changes in 1.6.3 (2016-05-05)
-----------------------------

* **Security notice:** Fixed calling ``clean()`` on the translations model.
* Fixed error with M2M relations to the translated model.
* Fixed ``UnicodeError`` in ``parler_tags``
* Show warning when translations are not initialized (when using management commands).


Changes in 1.6.2 (2016-03-08)
-----------------------------

* Added ``TranslatableModelMixin`` to handle complex model inheritance issues.
* Fixed tuple/list issues with ``fallbacks`` option.
* Fixed Python 3 `__str__()`` output for ``TranslatedFieldsModel``.
* Fixed output for ``get_language_title()`` when language is not configured.
* Fixed preserving GET args in admin change form view.


Changes in version 1.6.1 (2016-02-11)
-------------------------------------

* Fix queryset ``.dates()`` iteration in newer Django versions.
* Fixed Django 1.10 deprecation warnings in the admin.
* Avoided absolute URLs in language tabs.


Changes in version 1.6 (2015-12-29)
-----------------------------------

* Added Django 1.9 support
* Added support to generate ``PARLER_LANGUAGES`` from Django CMS' ``CMS_LANGUAGES``.
* Improve language variant support, e.g. ``fr-ca`` can fallback to ``fr``, and ``de-ch`` can fallback to ``de``.
* Dropped support for Django 1.4

(also released as 1.6b1 on 2015-12-16)


Changes in version 1.5.1 (2015-10-01)
-------------------------------------

* Fix handling for non-nullable ``ForeignKey`` in forms and admin.
* Fix performance of the admin list when ``all_languages_column`` or ``language_column`` is added to ``list_display`` (N-query issue).
* Fix support for other packages that replace the BoundField class in ``Form.__get_item__`` (namely django-slug-preview_).
* Fix editing languages that exist in the database but are not enabled in project settings.
* Fix DeprecationWarning for Django 1.8 in the admin.


Changes in version 1.5 (2015-06-30)
-----------------------------------

* Added support for multiple fallback languages!
* Added ``translatable-field`` CSS class to the ``<label>`` tags of translatable fields.
* Added ``{{ field.is_translatable }}`` variable.
* Added warning when saving a model without language code set.
  As of Django 1.8, ``get_language()`` returns ``None`` if no language is activated.
* Allow ``safe_translation_getter(default=..)`` to be a callable.
* Added ``all_languages_column``, inspired by aldryn-translation-tools_.
* Changed styling of ``language_column``, the items are now links to the language tabs.
* Fix caching support, the default timeout was wrongly imported.
* Fix Django 1.4 support for using ``request.resolver_match``.
* Fix admin delete translation view when using ``prefetch_related('translations')`` by default in the managers ``get_queryset()`` method.
* Fix using prefetched translations in ``has_translation()`` too.
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


.. _aldryn-translation-tools: https://github.com/aldryn/aldryn-translation-tools
.. _django-fluent-pages: https://github.com/edoburu/django-fluent-pages
.. _django-hvad: https://github.com/kristianoellegaard/django-hvad
.. _django-mptt: https://github.com/django-mptt/django-mptt
.. _django-polymorphic-tree: https://github.com/django-polymorphic/django-polymorphic-tree
.. _django-rest-framework: https://github.com/tomchristie/django-rest-framework
.. _django-slug-preview: https://github.com/edoburu/django-slug-preview
