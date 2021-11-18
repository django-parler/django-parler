Django compatibility
====================

This package has been tested with:

* Django versions 2.2 up to 4.0
* Python versions 3.6 and up

See the `the tox.ini file <https://github.com/django-parler/django-parler/blob/master/tox.ini>`_
for the compatibility testing matrix.

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

.. _ordering:

The ``ordering`` meta field
---------------------------

It's not possible to order on translated fields by default.
Django won't allow the following::

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFields

    class MyModel(TranslatableModel):
        translations = TranslatedFields(
            title = models.CharField(max_length=100),
        )

        class Meta:
            ordering = ('title',)  # NOT ALLOWED

        def __unicode__(self):
            return self.title

You can however, perform ordering within the queryset::

    MyModel.objects.translated('en').order_by('translations__title')

You can also use the provided classes to perform the sorting within Python code.

* For the admin :attr:`~django.contrib.admin.ModelAdmin.list_filter` use: :class:`~parler.admin.SortedRelatedFieldListFilter`
* For forms widgets use: :class:`~parler.widgets.SortedSelect`, :class:`~parler.widgets.SortedSelectMultiple`, :class:`~parler.widgets.SortedCheckboxSelectMultiple`


.. _admin-compat:

Using ``search_fields`` in the admin
------------------------------------

When translated fields are included in the :attr:`~django.contrib.admin.ModelAdmin.search_fields`,
they should be includes with their full ORM path. For example::

    from parler.admin import TranslatableAdmin

    class MyModelAdmin(TranslatableAdmin):
        search_fields = ('translations__title',)


Using ``prepopulated_fields`` in the admin
------------------------------------------

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
