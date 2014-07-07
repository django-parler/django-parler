Django compatibility
====================

This package has been tested with:

* Django versions 1.4, 1.5 and 1.6
* Python versions 2.6, 2.7 and 3.3

Django 1.4 note
---------------

When using Django 1.4, there is a small tweak you'll have to make in the admin.
Instead of using :attr:`~django.contrib.admin.ModelAdmin.fieldsets`, use ``declared_fieldsets``
on the :class:`~django.contrib.admin.ModelAdmin` definition.

The Django 1.4 admin validation doesn't actually check the form fields,
but only checks whether the fields exist in the model - which they obviously don't.
Using ``declared_fieldsets`` instead of ``fieldsets`` circumvents this check.

Using prepopulated_fields
-------------------------

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
