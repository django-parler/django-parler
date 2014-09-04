Django compatibility
====================

This package has been tested with:

* Django versions 1.4, 1.5 and 1.6
* Python versions 2.6, 2.7 and 3.3

.. _orm-restrictions:

Using multiple ``filter()`` calls
---------------------------------

Since translated fields live in a separate model,
they can be filtered like any normal relation::

    object = MyObject.objects.filter(translations__title='cheese omelet')

    translation1 = myobject.translations.all()[0]

However, if you have to query a language or translated attribute, this should happen in a single query.
That can either be a single
:func:`~django.db.models.query.QuerySet.filter`,
:func:`~parler.managers.TranslatableManager.translated` or
:func:`~parler.managers.TranslatableManager.active_translations`) call::

    from parler.utils import get_active_language_choices

    MyObject.objects.filter(
        translations__language_code__in=get_active_language_choices(),
        translations__slug='omelette'
    )

Queries on translated fields, even just ``.translated()`` spans a relationship.
Hence, they can't be combined with other filters on translated fields,
as that causes double joins on the translations table.
See `the ORM documentation <https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships>`_ for more details.

.. _admin-compat:

Django Admin compatibility
--------------------------

Almost every Django admin feature just works, there are a few special cases:

Using search_fields
~~~~~~~~~~~~~~~~~~~

When translated fields are included in the :attr:`~django.contrib.admin.ModelAdmin.search_fields`,
they should be includes with their full ORM path. For example::

    from parler.admin import TranslatableAdmin

    class MyModelAdmin(TranslatableAdmin):
        search_fields = ('translations__title',)


Using prepopulated_fields
~~~~~~~~~~~~~~~~~~~~~~~~~

Using :attr:`~django.contrib.admin.ModelAdmin.prepopulated_fields` doesn't work yet,
as the admin will complain that the field does not exist.
Use :func:`~django.contrib.admin.ModelAdmin.get_prepopulated_fields` as workaround::

    from parler.admin import TranslatableAdmin

    class MyModelAdmin(TranslatableAdmin):

        def get_prepopulated_fields(self, request, obj=None):
            # can't use `prepopulated_fields = ..` because it breaks the admin validation
            # for translated fields. This is the official django-parler workaround.
            return {
                'slug': ('title',)
            }

Using fieldsets in Django 1.4
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using Django 1.4, there is a small tweak you'll have to make in the admin.
Instead of using :attr:`~django.contrib.admin.ModelAdmin.fieldsets`, use ``declared_fieldsets``
on the :class:`~django.contrib.admin.ModelAdmin` definition.

The Django 1.4 admin validation doesn't actually check the form fields,
but only checks whether the fields exist in the model - which they obviously don't.
Using ``declared_fieldsets`` instead of ``fieldsets`` circumvents this check.
