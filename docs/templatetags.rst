.. _templatetags:

Template tags
=============

All translated fields can be read like normal fields.
The template tags provide additional utility features:

* Getting a translated URL of the current page, or any other object.
* Switching the object language, e.g. to display fields in a different language.
* Fetching translated fields in a thread-safe way (for shared objects).

When a translation is not available for the field,
an empty string (or :django:setting:`TEMPLATE_STRING_IF_INVALID`) will be outputted.
The Django template system safely ignores the :class:`~parler.models.TranslationDoesNotExist`
exception that would normally be emitted in code;
that's because that exception inherits from :class:`~exceptions.AttributeError`.

To use the template loads, add this to the top of the template:

.. code-block:: html+django

    {% load parler_tags %}


.. _get_translated_url:

Getting the translated URL
--------------------------

The ``get_translated_url`` tag can be used to get the proper URL for this page in a different language.
If the URL could not be generated, an empty string is returned instead.

This algorithm performs a "best effort" approach to give a proper URL.
When this fails, add the :class:`~parler.views.ViewUrlMixin` to your view to contruct the proper URL instead.

Example, to build a language menu:

.. code-block:: html+django

    {% load i18n parler_tags %}

    <ul>
        {% for lang_code, title in LANGUAGES %}
            {% get_language_info for lang_code as lang %}
            {% get_translated_url lang_code as tr_url %}
            {% if tr_url %}<li{% if lang_code == LANGUAGE_CODE %} class="is-selected"{% endif %}><a href="{{ tr_url }}" hreflang="{{ lang_code }}">{{ lang.name_local|capfirst }}</a></li>{% endif %}
        {% endfor %}
    </ul>

To inform search engines about the translated pages:

.. code-block:: html+django

   {% load i18n parler_tags %}

   {% for lang_code, title in LANGUAGES %}
       {% get_translated_url lang_code as tr_url %}
       {% if tr_url %}<link rel="alternate" hreflang="{{ lang_code }}" href="{{ tr_url }}" />{% endif %}
   {% endfor %}

.. note::

    Using this tag is not thread-safe if the object is shared between threads.
    It temporary changes the current language of the object.


Changing the object language
----------------------------

To switch an object language, use:

.. code-block:: html+django

    {% objectlanguage object "en" %}
      {{ object.title }}
    {% endobjectlanguage %}

A :class:`~parler.models.TranslatableModel` is not affected by the ``{% language .. %}`` tag
as it maintains it's own state. Using this tag temporary switches the object state.

.. note::

    Using this tag is not thread-safe if the object is shared between threads.
    It temporary changes the current language of the object.


Thread safety notes
-------------------

Using the ``{% get_translated_url %}`` or ``{% objectlanguage %}`` tags is not thread-safe if the object is shared between threads.
It temporary changes the current language of the view object.
Thread-safety is rarely an issue in templates, when all objects are fetched from the database in the view.

One example where it may happen, is when you have objects cached in global variables.
For example, attaching objects to the :class:`~django.contrib.sites.models.Site` model causes this.
A shared object is returned when these objects are accessed using ``Site.objects.get_current().my_object``.
That's because the sites framework keeps a global cache of all :class:`~django.contrib.sites.models.Site` objects,
and the ``my_object`` relationship is also cached by the ORM. Hence, the object is shared between all requests.

In case an object is shared between threads, a safe way to access the translated field
is by using the template filter ``get_translated_field`` or your own variation of it:

.. code-block:: html+django

    {{ object|get_translated_field:'name' }}

This avoids changing the ``object`` language with
a :func:`~parler.models.TranslatableModel.set_current_language` call.
Instead, it directly reads the translated field using :func:`~parler.models.TranslatableModel.safe_translation_getter`.
The field is fetched in the current Django template, and follows the project language settings (whether to use fallbacks, and ``any_language`` setting).
