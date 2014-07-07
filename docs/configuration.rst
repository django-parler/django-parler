Configuration options
=====================


.. _PARLER_DEFAULT_LANGUAGE_CODE:

PARLER_DEFAULT_LANGUAGE_CODE
----------------------------

The language code for the fallback language.
This language is used when a translation for the currently selected language does not exist.

By default, it's the same as :django:setting:`LANGUAGE_CODE`.

This value is used as input for ``PARLER_LANUAGES['default']['fallback']``.


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
            'fallback': 'en',             # defaults to PARLER_DEFAULT_LANGUAGE_CODE
            'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
        }
    }

The values in the ``default`` section are applied to all entries in the dictionary,
filling any missing values.

The following entries are available:

``code``
    The language code for the entry.

``fallback``
    The fallback language for the entry

``hide_untranslated``
    Whether untranslated objects should be returned by :func:`~parler.managers.TranslatableManager.active_translations`.

    * When ``True``, only the current language is returned, and no fallback language is used.
    * When ``False``, objects having either a translation or fallback are returned.

    The default is ``False``.


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
            'fallback': 'en',             # defaults to PARLER_DEFAULT_LANGUAGE_CODE
            'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
        }
    }


.. _PARLER_ENABLE_CACHING:

PARLER_ENABLE_CACHING
---------------------

::

    PARLER_ENABLE_CACHING = True

If needed, caching can be disabled.
This is likely not needed.

.. _PARLER_SHOW_EXCLUDED_LANGUAGE_TABS:

PARLER_SHOW_EXCLUDED_LANGUAGE_TABS
----------------------------------

::

    PARLER_SHOW_EXCLUDED_LANGUAGE_TABS = False

By default, the admin tabs are limited to the language codes found in :django:setting:`LANGUAGES`.
If the models have other translations, they can be displayed by setting this value to ``True``.
