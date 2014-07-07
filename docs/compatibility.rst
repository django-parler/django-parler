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
