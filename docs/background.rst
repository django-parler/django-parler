Background
==========

A brief history
---------------

This package is inspired by django-hvad_. When attempting to integrate multilingual
support into django-fluent-pages_ using django-hvad_ this turned out to be really hard.
The sad truth is that while django-hvad_ has a nice admin interface, table layout and model API,
it also overrides much of the default behavior of querysets and model metaclasses.
This prevents combining django-hvad_ with django-polymorphic_ or django-mptt_ for example.

When investigating other multilingual packages, they either appeared to be outdated,
store translations in the same table (too inflexible for us) or only provided a model API.
Hence, there was a need for a new solution, using a simple, crude but effective API.

To start multilingual support in our django-fluent-pages_ package, it was coded directly into the package itself.
A future django-hvad_ transition was kept in mind. Instead of doing metaclass operations,
the "shared model" just proxied all attributes to the translated model (all manually constructed).
Queries just had to be performed using ``.filter(translations__title=..)``.
This proved to be a sane solution and quickly it turned out that this code
deserved a separate package, and some other modules needed it too.

This package is an attempt to combine the best of both worlds;
the API simplicity of django-hvad_ with the crude,
but effective solution of proxying translated attributes.

Added on top of that, the API-sugar is provided, similar to what django-hvad has.
It's possible to create the translations model manually,
or let it be created dynamically when using the :class:`~parler.models.TranslatedFields` field.
This is to make your life easier - without loosing the freedom of manually using the API at your will.


Presentations
-------------

* django-parler - DjangoCon EU 2014 lightning talk
  https://speakerdeck.com/vdboor/django-parler-djangocon-eu-2014-lightning-talk


Database schema
---------------

django-parler uses a separate table for storing translated fields.
Each row stores the content for one language, using a ``language_code`` column.

.. image:: /images/parler-models.png
   :alt: django-parler database design
   :width: 499
   :height: 410

The same database layout is used by django-hvad_, making a transition to django-parler rather easy.

Advantages:

* Works with existing tools, such as the Django migration framework.
* Unlimited languages can be supported
* Languages can be added on the fly, no database migrations needed.

Disadvantages:

* An extra database query is needed to fetch translated fields.
* Filtering on translated fields should happen in a single ``.filter(..)`` call.

Solutions:

* The extra database queries are mostly avoided by the caching mechanism,
  which can store the translated fields in memcached.
* To query all languages, use ``.prefetch('translations')`` in the ORM query.
  The prefetched data will be read by django-parler.


Opposite design: django-modeltranslation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The classic solution for writing translatable fields is employed by django-modeltranslation_.
Each field has a separate column per language.

.. image:: /images/modeltranslation.png
   :alt: django-modeltranslation database design
   :width: 625
   :height: 508

The advantages are:

* fast reading of all the data, everything is in a single table.
* editing all fields at once is easy.

The disadvantages are:

* The database schema is changed based on the project settings.
* Third party packages can't provide reasonable data migrations for translated fields.
* For projects with a large number of languages, a lot of additional fields will be read with each query,


Package naming
--------------

The package name is rather easy to explain; "parler" is French for "to talk".

And for `our slogan <http://urbandictionary.com/define.php?term=Omelette+du+fromage>`_,
watch Dexter's Laboratory episode "The Big Cheese". ;-)


.. _django-hvad: https://github.com/kristianoellegaard/django-hvad
.. _django-mptt: https://github.com/django-mptt/django-mptt
.. _django-fluent-pages: https://github.com/edoburu/django-fluent-pages
.. _django-modeltranslation: https://github.com/deschler/django-modeltranslation
.. _django-polymorphic: https://github.com/django-polymorphic/django-polymorphic
