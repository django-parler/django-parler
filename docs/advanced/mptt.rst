Integration with django-mptt
============================

When you have to combine :class:`~parler.models.TranslatableModel`
with :class:`~mptt.models.MPTTModel` you
have to make sure the model managers of both classes are combined too.

This can be done by extending the :class:`~django.db.models.Manager`
and :class:`~django.db.models.query.QuerySet` class.

.. note:: This example is written for django-mptt_ >= 0.7.0,
          which also requires combining the queryset classes.

For a working example, see django-categories-i18n_.


Combining ``TranslatableModel`` with ``MPTTModel``
--------------------------------------------------

Say we have a base ``Category`` model that needs to be translatable:

.. code-block:: python

    from django.db import models
    from django.utils.encoding import python_2_unicode_compatible, force_text
    from parler.models import TranslatableModel, TranslatedFields
    from parler.managers import TranslatableManager
    from mptt.models import MPTTModel
    from .managers import CategoryManager
    

    @python_2_unicode_compatible
    class Category(MPTTModel, TranslatableModel): # MPTTModel must be 1st
        # The shared base model. Either place translated fields here,
        # or place them at the subclasses (see note below).
        parent = models.ForeignKey('self', related_name='children')
        
        translations = TranslatedFields(
            name=models.CharField(blank=False, default='', max_length=128),
            slug=models.SlugField(blank=False, default='', max_length=128)
        )

        objects = CategoryManager()

        def __str__(self):
            return self.safe_translation_getter('name', any_language=True)


Combining managers
------------------

The managers can be combined by inheriting them.
Unfortunately, django-mptt_ 0.7 overrides the ``get_querset()`` method,
so it needs to be redefined:

.. code-block:: python

        import django
        from parler.managers import TranslatableManager, TranslatableQuerySet
        from mptt.managers import TreeManager
        from mptt.querysets import TreeQuerySet  # new as of mptt 0.7


        class CategoryQuerySet(TranslatableQuerySet, TreeQuerySet):
            pass

            # Optional: make sure the Django 1.7 way of creating managers works.
            def as_manager(cls):
                manager = CategoryManager.from_queryset(cls)()
                manager._built_with_as_manager = True
                return manager
            as_manager.queryset_only = True
            as_manager = classmethod(as_manager)


        class CategoryManager(TreeManager, TranslatableManager):
            queryset_class = CategoryQuerySet

            def get_queryset(self):
                # This is the safest way to combine both get_queryset() calls
                # supporting all Django versions and MPTT 0.7.x versions
                return self.queryset_class(self.model, using=self._db).order_by(self.tree_id_attr, self.left_attr)

            if django.VERSION < (1,6):
                get_query_set = get_queryset


Assign the manager to the model ``objects`` attribute.


Implementing the admin
----------------------

By merging the base classes, the admin interface supports translatable MPTT models:

.. code-block:: python

    from django.contrib import admin
    from parler.admin import TranslatableAdmin, TranslatableModelForm
    from mptt.admin import MPTTModelAdmin
    from mptt.forms import MPTTAdminForm
    from .models import Category


    class CategoryAdminForm(MPTTAdminForm, TranslatableModelForm):
        pass


    class CategoryAdmin(TranslatableAdmin, MPTTModelAdmin):
        form = CategoryAdminForm
        
        def get_prepopulated_fields(self, request, obj=None):
            return {'slug': ('title',)}  # needed for translated fields


    admin.site.register(Category, CategoryAdmin)

.. _django-mptt: https://github.com/django-mptt/django-mptt
.. _django-categories-i18n: https://github.com/edoburu/django-categories-i18n
