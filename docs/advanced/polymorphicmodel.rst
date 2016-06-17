Integration with django-polymorphic
===================================

When you have to combine :class:`~parler.models.TranslatableModel`
with :class:`~polymorphic.models.PolymorphicModel` you
have to make sure the model managers of both classes are combined too.

This can be done by either overwriting :ref:`default_manager <custom-managers-and-inheritance>`
or by extending the :class:`~django.db.models.Manager` and :class:`~django.db.models.query.QuerySet` class.


Combining ``TranslatableModel`` with ``PolymorphicModel``
---------------------------------------------------------

Say we have a base ``Product`` with two concrete products, a ``Book`` with two translatable fields
``name`` and ``slug``, and a ``Pen`` with one translatable field ``identifier``. Then the following
pattern works for a polymorphic Django model:

.. code-block:: python

	from django.db import models
	from django.utils.encoding import python_2_unicode_compatible, force_text
	from parler.models import TranslatableModel, TranslatedFields
	from parler.managers import TranslatableManager
	from polymorphic import PolymorphicModel
	from .managers import BookManager
	

	class Product(PolymorphicModel):
	    # The shared base model. Either place translated fields here,
	    # or place them at the subclasses (see note below).
	    code = models.CharField(blank=False, default='', max_length=16)
	    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)


	@python_2_unicode_compatible
	class Book(Product, TranslatableModel):
	    # Solution 1: use a custom manager that combines both.
	    objects = BookManager()
	
	    translations = TranslatedFields(
	        name=models.CharField(blank=False, default='', max_length=128),
	        slug=models.SlugField(blank=False, default='', max_length=128)
	    )
	
	    def __str__(self):
	        return force_text(self.code)


	@python_2_unicode_compatible
	class Pen(TranslatableModel, Product):
	    # Solution 2: override the default manager.
	    default_manager = TranslatableManager()
	
	    translations = TranslatedFields(
	        identifier=models.CharField(blank=False, default='', max_length=255)
	    )
	
	    def __str__(self):
	        return force_text(self.identifier)

The only precaution one must take, is to override the default manager in each of the classes
containing translatable fields. This is shown in the example above.

As of django-parler 1.2 it's possible to have translations on both the base and derived models.
Make sure that the field name (in this case ``translations``) differs between both models,
as that name is used as ``related_name`` for the translated fields model


Combining managers
------------------

The managers can be combined by inheriting them, and specifying
the :attr:`~parler.managers.TranslatableManager.queryset_class` attribute
with both *django-parler* and django-polymorphic_ use.

.. code-block:: python

        from parler.managers import TranslatableManager, TranslatableQuerySet
        from polymorphic import PolymorphicManager
        from polymorphic.query import PolymorphicQuerySet


        class BookQuerySet(TranslatableQuerySet, PolymorphicQuerySet):
            pass

        class BookManager(PolymorphicManager, TranslatableManager):
            queryset_class = BookQuerySet

Assign the manager to the model ``objects`` attribute.


Implementing the admin
----------------------

It is perfectly possible to to register individual polymorphic models in the Django admin interface.
However, to use these models in a single cohesive interface, some extra base classes are available.

This admin interface adds translatable fields to a polymorphic model:

.. code-block:: python

	from django.contrib import admin
	from parler.admin import TranslatableAdmin, TranslatableModelForm
	from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin
	from .models import BaseProduct, Book, Pen


	class BookAdmin(TranslatableAdmin, PolymorphicChildModelAdmin):
	    base_form = TranslatableModelForm
	    base_model = BaseProduct
	    base_fields = ('code', 'price', 'name', 'slug')
	
	class PenAdmin(TranslatableAdmin, PolymorphicChildModelAdmin):
	    base_form = TranslatableModelForm
	    base_model = BaseProduct
	    base_fields = ('code', 'price', 'identifier',)
	
	class BaseProductAdmin(PolymorphicParentModelAdmin):
	    base_model = BaseProduct
	    child_models = ((Book, BookAdmin), (Pen, PenAdmin),)
	    list_display = ('code', 'price',)
	
	admin.site.register(BaseProduct, BaseProductAdmin)

.. _django-polymorphic: https://github.com/django-polymorphic/django-polymorphic
