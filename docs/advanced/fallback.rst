Translations without fallback languages
=======================================

When a translation is missing, the fallback languages are used.
However, when an object has no fallback languages, this still fails.

There are a few solutions to this problem:

1. Declare the translated attribute explicitly with ``any_language=True``::

        from parler.models import TranslatableModel
        from parler.fields import TranslatedField

        class MyModel(TranslatableModel):
            title = TranslatedField(any_language=True)

   Now, the title will try to fetch one of the existing languages from the database.

2. Use :func:`~parler.models.TranslatableModel.safe_translation_getter` on attributes
   which don't have an ``any_language=True`` setting. For example::

        model.safe_translation_getter("fieldname", any_language=True)

3. Catch the :class:`~parler.models.TranslationDoesNotExist` exception. For example::

        try:
            return object.title
        except TranslationDoesNotExist:
            return ''

   Because this exception inherits from :class:`~exceptions.AttributeError`,
   templates already display empty values by default.

4. Avoid fetching untranslated objects using queryset methods. For example::

        queryset.active_translations()

   Which is almost identical to::

        codes = get_active_language_choices()
        queryset.filter(translations__language_code__in=codes).distinct()

   Note that the same `ORM restrictions <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_ apply here.
