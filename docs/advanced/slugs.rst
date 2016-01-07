Using translated slugs in views
===============================

To handle translatable slugs in the :class:`~django.views.generic.detail.DetailView`,
the :class:`~parler.views.TranslatableSlugMixin` can be used to make this work smoothly.
For example:

.. code-block:: python

    class ArticleDetailView(TranslatableSlugMixin, DetailView):
        model = Article
        template_name = 'article/details.html'

The :class:`~parler.views.TranslatableSlugMixin` makes sure that:

* The object is fetched in the proper translation.
* The slug field is read from the translation model, instead of the shared model.
* Fallback languages are handled.
* Objects are not accidentally displayed in their fallback slugs, but redirect to the translated slug.
