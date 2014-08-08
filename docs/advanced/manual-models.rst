Constructing the translations model manually
============================================

It's also possible to create the translated fields model manually:

.. code-block:: python

    from django.db import models
    from parler.models import TranslatableModel, TranslatedFieldsModel
    from parler.fields import TranslatedField


    class MyModel(TranslatableModel):
        title = TranslatedField()  # Optional, explicitly mention the field

        class Meta:
            verbose_name = _("MyModel")

        def __unicode__(self):
            return self.title


    class MyModelTranslation(TranslatedFieldsModel):
        master = models.ForeignKey(MyModel, related_name='translations', null=True)
        title = models.CharField(_("Title"), max_length=200)

        class Meta:
            unique_together = ('language_code', 'master')
            verbose_name = _("MyModel translation")

This has the same effect, but also allows to to override
the :func:`~django.db.models.Model.save` method, or add new methods yourself.
