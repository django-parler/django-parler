Combining TranslatableModel with PolymorphicModel
=================================================

Sometimes you may want to combine a TranslatableModel with PolymorphicModel. Since both classes
are abstract, both inherit from ``models.Model`` and both override the model manager, one must take
care to override the default manager.

This pattern works for a polymorphic Django model:

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

Here the two products ``Book`` and ``Pen`` inherit from a common base class ``Product``. They both
contain translatable fields. The only precaution one must take, is to override the
``default_manager`` in each of the class containing translatable fields, as shown above.
