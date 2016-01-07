Performance guidelines
======================

The translations of each model is stored in a separate table.
In some cases, this may cause in N-query issue.
*django-parler* offers two ways to handle the performance of the dabase.

Caching
-------

All translated contents is cached by default.
Hence, when an object is read again, no query is performed.
This works out of the box when the project uses a proper caching:

.. code-block:: python

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'KEY_PREFIX': 'mysite.production',  # Change this
            'LOCATION': '127.0.0.1:11211',
            'TIMEOUT': 24*3600
        },
    }

You have to make sure your project has the proper backend support available::

    pip install python-memcached

Now, the translation table only has to be read once per day.

Query prefetching
-----------------

By using :func:`~django.db.models.query.QuerySet.prefetch_related`,
all translations can be fetched in a single query:

.. code-block:: python

    object_list = MyModel.objects.prefetch_related('translations')
    for obj in object_list:
        print obj.title  # reads translated title from the prefetched queryset

Note that the prefetch reads the information of all languages,
not just the currently active language.

When you display translated objects in a form, e.g. a select list, you can prefetch the queryset too:

.. code-block:: python

    class MyModelAdminForm(TranslatableModelForm):
        def __init__(self, *args, **kwargs):
            super(MyModelAdminForm, self).__init__(*args, **kwargs)
            self.fields['some_field'].queryset = self.fields['some_field'].queryset.prefetch_related('translations')

