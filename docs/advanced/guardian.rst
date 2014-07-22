Integration with django-guardian
================================

Combining ``TranslatableAdmin`` with ``GuardedModelAdmin``
----------------------------------------------------------

To combine the :class:`~parler.admin.TranslatableAdmin`
with the :class:`~guardian.admin.GuardedModelAdmin` from django-guardian_
there are a few things to notice.

Depending on the order of inheritance, either the parler language tabs
or guardian "Object permissions" button may not be visible anymore.

To fix this you'll have to make sure both template parts are included in the page.

Both classes override the :attr:`~django.contrib.admin.ModelAdmin.change_form_template` value:

* :class:`~guardian.admin.GuardedModelAdmin` sets it to ``admin/guardian/model/change_form.html`` explicitly.
* :class:`~parler.admin.TranslatableAdmin` sets it to ``admin/parler/change_form.html``,
  but it inherits the original template that the admin would have auto-selected otherwise.


Using ``TranslatableAdmin`` as first class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the :class:`~parler.admin.TranslatableAdmin` is the first inherited class:

.. code-block:: python

    class ProjectAdmin(TranslatableAdmin, GuardedModelAdmin):
        pass

You can create a template such as ``myapp/project/change_form.html``
which inherits the guardian template:

.. code-block:: html+django

    {% extends "admin/guardian/model/change_form.html" %}

Now, *django-parler* will load this template in ``admin/parler/change_form.html``,
so both the guardian and parler content is visible.


Using ``GuardedModelAdmin`` as first class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the :class:`~guardian.admin.GuardedModelAdmin` is the first inherited class:

.. code-block:: python

    class ProjectAdmin(TranslatableAdmin, GuardedModelAdmin):
        change_form_template = 'myapp/project/change_form.html'

The ``change_form_template`` needs to be set manually.
It can either be set to ``admin/parler/change_form.html``,
or use a custom template that includes both bits:

.. code-block:: html+django

    {% extends "admin/guardian/model/change_form.html" %}

    {# restore django-parler tabs #}
    {% block field_sets %}
    {% include "admin/parler/language_tabs.html" %}
    {{ block.super }}
    {% endblock %}


.. _django-guardian: https://github.com/lukaszb/django-guardian
