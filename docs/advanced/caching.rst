Disabling caching
-----------------

If desired, caching of translated fields can be disabled
by adding :ref:`PARLER_ENABLE_CACHING = False <PARLER_ENABLE_CACHING>` to the settings.


Parler on more sites with same cache
------------------------------------

If Parler runs on multiple sites that share the same cache, it is necessary
to set a different prefix for each site
by adding :ref:`PARLER_CACHE_PREFIX = 'mysite' <PARLER_CACHE_PREFIX>` to the settings.
