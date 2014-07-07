Welcome to django-parler's documentation!
=========================================

    "Easily translate "cheese omelet" into "omelette du fromage".

django-parler provides Django model translations without nasty hacks.

Features:

* Nice admin integration.
* Access translated attributes like regular attributes.
* Automatic fallback to the default language.
* Separate table for translated fields, compatible with django-hvad_.
* Plays nice with others, compatible with django-polymorphic_, django-mptt_ and such:

 * No ORM query hacks.
 * Easy to combine with custom Manager or QuerySet classes.
 * Easy to construct the translations model manually when needed.

Getting started
---------------

.. toctree::
   :maxdepth: 2

   quickstart
   templatetags
   configuration

In depth topics
---------------

.. toctree::
   :maxdepth: 2

   advanced
   compatibility
   background


API documentation
-----------------

.. toctree::
   :maxdepth: 2

   api/index
   changelog


Roadmap
=======

The following features are on the radar for future releases:

* Multi-level model inheritance support
* Improve query usage, e.g. by adding "Prefetch" objects.

Please contribute your improvements or work on these area's!


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _django-hvad: https://github.com/kristianoellegaard/django-hvad
.. _django-mptt: https://github.com/django-mptt/django-mptt
.. _django-polymorphic: https://github.com/chrisglass/django_polymorphic
