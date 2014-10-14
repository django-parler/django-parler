Adding translated fields to an existing model
=============================================

Create a proxy class::

    from django.contrib.sites.models import Site
    from parler.models import TranslatableModel, TranslatedFields


    class TranslatableSite(TranslatableModel, Site):
        class Meta:
            proxy = True

        translations = TranslatedFields()


And update the admin::

    from django.contrib.sites.admin import SiteAdmin
    from django.contrib.sites.models import Site
    from parler.admin import TranslatableAdmin, TranslatableStackedInline


    class NewSiteAdmin(TranslatableAdmin, SiteAdmin):
        pass

    admin.site.unregister(Site)
    admin.site.register(TranslatableSite, NewSiteAdmin)


Overwriting existing untranslated fields
----------------------------------------

Note that it is not possible to add translations in the proxy class with the same
name as fields in the parent model. This will not show up as an error, but it
will cause translations to overwrite other languages and cause great confusion
and ambiguity. Instead, opt for reading :doc:`migrating`.
