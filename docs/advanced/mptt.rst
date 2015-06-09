Integration with django-mptt
============================

When you have to combine :class:`~parler.models.TranslatableModel`
with :class:`~mptt.models.MPTTModel` you
have to make sure the model managers of both classes are combined too.

This can be done by extending the :class:`~django.db.models.Manager`
and :class:`~django.db.models.query.QuerySet` class.

.. note:: This example is written for django-mptt_ >= 0.7.0,
          which also requires combining the queryset classes.


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
    class Category(TranslatableModel, MPTTModel):
        # The shared base model. Either place translated fields here,
        # or place them at the subclasses (see note below).
        parent = models.ForeignKey('self', related_name='children')
        
        translations = TranslatedFields(
            name=models.CharField(blank=False, default='', max_length=128),
            slug=models.SlugField(blank=False, default='', max_length=128)
        )

        objects = CategoryManager()

        def __str__(self):
            return force_text(self.code)


Combining managers
------------------

The managers can be combined by inheriting them.
Unfortunately, django-mptt_ 0.7 overrides the ``get_querset()`` method,
so it needs to be redefined:

.. code-block:: python

        from parler.managers import TranslatableManager, TranslatableQuerySet
        from mptt.managers import TreeManager
        from mptt.querysets import TreeQuerySet  # new as of mptt 0.7


        class CategoryQuerySet(TranslatableQuerySet, MPTTQuerySet):
            pass

        class CategoryManager(TreeManager, TranslatableManager):
            queryset_class = CategoryQuerySet

            def get_queryset(self):
                # Nasty: As of django-mptt 0.7, TreeManager.get_querset() no longer calls super(), breaking integration.
                # Hence, redefine get_queryset() here to have the logic from django-parler and django-mptt.
                return self.queryset_class(self.model, using=self._db).order_by(self.tree_id_attr, self.left_attr)


Assign the manager to the model ``objects`` attribute.


Implementing the admin
----------------------

By merging the base classes, the admin interface supports translatable MPTT models:

.. code-block:: python

    from django.contrib import admin
    from parler.admin import TranslatableAdmin, TranslatableModelForm
    from mptt.admin import MPTTModelAdmin
    from .models import Category


    class CategoryAdmin(TranslatableAdmin, MPTTModelAdmin):
        pass

    admin.site.register(Category, CategoryAdmin)

.. _django-mptt: https://github.com/django-mptt/django-mptt
