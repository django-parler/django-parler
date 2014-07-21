Combining TranslatableModel with PolymorphicModel
=================================================

Sometimes you may want to combine :class:`~parler.models.TranslatableModel` with :class:`~polymorphic.models.PolymorphicModel`.
Since both classes are abstract, inherit from ``models.Model`` and both override the model manager, one must
take care to also override the default manager.

Say we have a base ``Product`` with two concrete products, a ``Book`` with two translatable fields
``name`` and ``slug``, and a ``Pen`` with one translatable field ``identifier``. Then the following
pattern works for a polymorphic Django model:

.. code-block:: python

	from django.db import models
	from django.utils.encoding import python_2_unicode_compatible, force_text
	from parler.models import TranslatableModel, TranslatedFields
	from parler.managers import TranslatableManager
	from polymorphic import PolymorphicModel
	
	class Product(PolymorphicModel):
	    code = models.CharField(blank=False, default='', max_length=16)
	    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
	
	@python_2_unicode_compatible
	class Book(TranslatableModel, Product):
	    default_manager = TranslatableManager()
	
	    translations = TranslatedFields(
	        name=models.CharField(blank=False, default='', max_length=128),
	        slug=models.SlugField(blank=False, default='', max_length=128)
	    )
	
	    def __str__(self):
	        return force_text(self.code)
	
	@python_2_unicode_compatible
	class Pen(TranslatableModel, Product):
	    default_manager = TranslatableManager()
	
	    translations = TranslatedFields(
	        identifier=models.CharField(blank=False, default='', max_length=255)
	    )
	
	    def __str__(self):
	        return force_text(self.identifier)

The only precaution one must take, is to override the default manager in each of the classes
containing translatable fields. This is shown in the example above.

It is perfectly possible to to register individual polymorphic models in the Django admin interface.
However, to use these models in a single cohesive interface, some extra base classes are available.

This admin interface adds translatable fields to a polymorphic model:

.. code-block:: python

	from django.contrib import admin
	from parler.admin import TranslatableAdmin, TranslatableModelForm
	from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin
	from myapp.models.myproduct import BaseProduct, Book, Pen
	
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

.. note:: You need at least `django-polymorphic <https://github.com/chrisglass/django_polymorphic>`_ >= 0.5.5 in order to get this working.

