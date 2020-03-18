Configuration options
=====================


.. _PARLER_DEFAULT_LANGUAGE_CODE:

PARLER_DEFAULT_LANGUAGE_CODE
----------------------------

The language code for the fallback language.
This language is used when a translation for the currently selected language does not exist.

By default, it's the same as :django:setting:`LANGUAGE_CODE`.

This value is used as input for ``PARLER_LANGUAGES['default']['fallback']``.


.. _PARLER_LANGUAGES:

PARLER_LANGUAGES
----------------

The configuration of language defaults.
This is used to determine the languages in the ORM and admin.

::

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

The values in the ``default`` section are applied to all entries in the dictionary,
filling any missing values.

The following entries are available:

``code``
    The language code for the entry.

``fallbacks``
    The fallback languages for the entry

    .. versionchanged:: 1.5
       In the previous versions, this field was called ``fallback`` and pointed to a single language.
       The old setting name is still supported, but it's recommended you upgrade your settings.

``hide_untranslated``
    Whether untranslated objects should be returned by :func:`~parler.managers.TranslatableManager.active_translations`.

    * When ``True``, only the current language is returned, and no fallback language is used.
    * When ``False``, objects having either a translation or fallback are returned.

    The default is ``False``.

.. _multisite-configuration:

Multi-site support
~~~~~~~~~~~~~~~~~~

When using the sites framework (:mod:`django.contrib.sites`) and the :django:setting:`SITE_ID`
setting, the dict can contain entries for every site ID. The special ``None`` key is no longer used::

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
            'fallbacks': ['en'],          # defaults to PARLER_DEFAULT_LANGUAGE_CODE
            'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
        }
    }

In this example, each language variant only display 2 tabs in the admin,
while the global site has an overview of all languages.


.. _PARLER_ENABLE_CACHING:

PARLER_ENABLE_CACHING
---------------------

::

    PARLER_ENABLE_CACHING = True

This setting is strictly for experts or for troubleshooting situations, where disabling caching can be beneficial.

.. _PARLER_CACHE_PREFIX:

PARLER_CACHE_PREFIX
-------------------

::

    PARLER_CACHE_PREFIX = ''

Prefix for sites that share the same cache. For example Aldryn News & Blog.


.. _PARLER_SHOW_EXCLUDED_LANGUAGE_TABS:

PARLER_SHOW_EXCLUDED_LANGUAGE_TABS
----------------------------------

::

    PARLER_SHOW_EXCLUDED_LANGUAGE_TABS = False

By default, the admin tabs are limited to the language codes found in :django:setting:`LANGUAGES`.
If the models have other translations, they can be displayed by setting this value to ``True``.


PARLER_DEFAULT_ACTIVATE
----------------------------------

::

    PARLER_DEFAULT_ACTIVATE = True

Setting, which allows to display translated texts in the default language even through ``translation.activate()`` is not called yet.
