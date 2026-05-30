:orphan:

..
    NB :orphan: tag required because this document is not part of any toctree
                but just included from another page. Without the tag, sphinx issues a warning

Some technical considerations about caching
===========================================

.. versionadded 2.x

When fixing the cache overlap issue in Parler <=2.3, several solutions have been considered:

    a) Include the database name in the cache key, to have separate cache for each model in each DB. This requires an additional parameter to ``get_translation_cache_key``, to be provided by every user of this function (5 of them, all in cache.py module, + a couple of tests).

    b) Leave the key unchanged, but use a separate cache for each database. This requires:

        - Configuring a CACHE for each DATABASE (in the settings)
        - Adding a check at startup to make sure configuration fulfills the above constraint.
        - Adapting the 5 methods actually interacting with the cache: ``cache.xxx`` becomes ``caches[db_alias].xxx``.

Both solutions make it necessary to use the db alias associated to each model, which is actually available in any ``<model_instance>._state.db``.

Solution a) was selected since it is 100% transparent to the users while solution b) would force an update on the cache configuration in the settings of every multi-db project.