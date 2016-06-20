Integration with django-rest-framework
======================================

To integrate the translated fields in django-rest-framework,
the django-parler-rest_ module provides serializer fields.
These fields can be used to integrate translations into the REST output.

Example code
------------

The following Country model will be exposed:

.. code-block:: python

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFields

    class Country(TranslatableModel):
        code = models.CharField(_("Country code"), max_length=2, unique=True, primary_key=True, db_index=True)

        translations = TranslatedFields(
            name = models.CharField(_("Name"), max_length=200, blank=True)
        )

        def __unicode__(self):
            self.name

        class Meta:
            verbose_name = _("Country")
            verbose_name_plural = _("Countries")


The following code is used in the serializer:

.. code-block:: python

    from parler_rest.serializers import TranslatableModelSerializer
    from parler_rest.fields import TranslatedFieldsField
    from myapp.models import Country

    class CountrySerializer(TranslatableModelSerializer):
        translations = TranslatedFieldsField(shared_model=Country)

        class Meta:
            model = Country
            fields = ('code', 'translations')


.. _django-parler-rest: https://github.com/django-parler/django-parler-rest
