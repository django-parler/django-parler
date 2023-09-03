:orphan:

..
    NB :orphan: tag required because this document is not part of any toctree
                but just included from another page. Without the tag, sphinx issues a warning

About the routing of ``save()`` calls
=====================================

.. versionadded 2.x:

This table summarizes how :func:`~TranslatableModelMixin.save` discriminates the various actions to be taken when called:

First, we need to know whether we are the model is new and being saved for the first time, being saved again in the same database, or being saved in a new database:

* If ``_state.db`` is None, we are saving **for the 1st time**.

    The destination database is either the one defined y the database router, or the one provided by the user in the ``using="xxx"`` parameter, if any.

* If ``_state.db`` is not None:
    - If the ``using="xxx"`` parameter is absent or same as ``_state.db``, we are saving **in the same DB**.
    - Else we are saving **in another DB**.

Next, the action is defined according to this table, based on the previously defined category, the value of the model's primary key (which may have been tampered with by the caller), and the value of the primary key as known after the last save (``_last_saved_pk``, which is internal and reliable) :

+--------------------------------------+--------------------+-------------------------+-------------------------+
|                                      | For the 1st time   | In same DB              | In another DB           |
+=============+========================+====================+=========================+=========================+
| pk = None   | last_saved_pk = None   | Regular first save | *IMPOSSIBLE*            | *IMPOSSIBLE*            |
|             +------------------------+--------------------+-------------------------+-------------------------+
|             | last_saved_pk not None | *IMPOSSIBLE*       | Duplication in same DB  | Duplication in new DB   |
+-------------+------------------------+--------------------+-------------------------+-------------------------+
| pk not None | last_saved_pk = None   | Regular first save | *IMPOSSIBLE*            | *IMPOSSIBLE*            |
|             +------------------------+--------------------+-------------------------+-------------------------+
|             | last_saved_pk = pk     | *IMPOSSIBLE*       | Regular update          | Overwrite/Duplicate [1] |
|             +------------------------+--------------------+-------------------------+-------------------------+
|             | last_saved_pk != pk    | *IMPOSSIBLE*       | Overwrite/Duplicate [1] | Overwrite/Duplicate [1] |
+-------------+------------------------+--------------------+-------------------------+-------------------------+

.. [1] This is an overwrite if the pk is already in use in the destination database (which is **not** supported by Parler) and a duplication with forced primary key otherwise (which is accepted by Parler).


