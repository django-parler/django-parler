Caching in Django-parler
========================

Django-parler provides a transparent caching feature, using the ``default cache`` configured by django setting ``CACHES``.

Disabling caching
-----------------

If desired, caching of translated fields can be disabled
by adding :ref:`PARLER_ENABLE_CACHING = False <PARLER_ENABLE_CACHING>` to the settings.


Parler on more sites with same cache
------------------------------------

If Parler runs on multiple sites that share the same cache, it is necessary
to set a different prefix for each site
by adding :ref:`PARLER_CACHE_PREFIX = 'mysite' <PARLER_CACHE_PREFIX>` to the settings.


Parler caching with multiple database
-------------------------------------

.. versionchanged 2.x:: The use of the cache by Django-parler <= 2.3 caused cache overlap across databases with problematic side-effects.

Parler caching can be used safely when using multiple databases: models retrieved from different databases are now use distinct cache keys.

Technical design information can be found on :doc:`this page <cache_design>`.

