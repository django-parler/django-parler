Migrating existing models
=========================

This guide is on how to move from an untranslated model to a model that contains translated
fields of the same name as your old untranslated fields.

Challenge: Populating translation tables

Normally, a TranslatableModel will store its translatable data in seperate
translation tables, and at least one row of data has to exist for a given "master" record.
This puts forward the following process:
  
 1. Retain existing columns
 2. Create the translation tables
 3. Populate the existing language into the new tables, removing the old rows.
  
Let's put this into code. Say we have the following model::
  
    class MyModel(models.Model):
        name = models.CharField(max_length=123)


Now, we need a translatable version, so we do the following::

    class MyModel(TranslatableModel):
        name = models.CharField(max_length=123)

        translations = TranslatedFields(
              name=models.CharField(max_length=123),
        )


The, we run ``manage.py schemamigration myapp --auto``. This creates the table for MyModelTranslation.

Manual migration
----------------

Now that MyModelTranslation exists, we can put data in it. To do that, we can execute the following code or create a datamigration (see after).::

    from django.conf import settings
    for obj in MyModel.objects.all():
         MyModelTranslation.objects.create(master=obj, name=obj.name, language_code=settings.LANGUAGE_CODE)


Naturally, you should still be using the same ``settings.LANGUAGE_CODE`` as
your original model data was written in. Just beware that if
settings.LANGUAGE_CODE is for instance "de-DE" but you only use "de"
in your parler languages, then you should just put "de" in the
language_code field.


Data migration
--------------

Instead of the above approach, it is much better to create a data migration with
``manage.py datamigration myapp populate_mymodel``.

Now navigate to the new data migration and write the migration, it goes
something like this:::
  
    def forwards(self, orm):
        "Write your forwards methods here."
        from django.conf import settings
        for obj in orm['myapp.MyModel'].objects.all():
            orm['myapp.MyModelTranslation'].objects.create(
                master=obj,
                language_code=settings.LANGUAGE_CODE,
                name=obj.name,
            )


NB! Read the note about settings.LANGUAGE_CODE in the previous section.


Finalizing
----------

But! We are not there yet. The original field ``name`` still has to be removed from MyModel,
otherwise there will be errors in django-parler. Thus, the example model should simply
look like this:::

    class MyModel(models.Model):
        pass


Now, you can test that you can create and use translations through the django admin backend.
If successful, create a new schemamigration to permanently remove the original ``name`` field.


Refactoring
-----------

After you have completed the change-over, you need to be vary of the various changes imposed.

Using ``values("relation__name")`` is suddenly not very nice, for instance in aggregate queries.

When you are doing ``filter(field_name)``, you should instead do ``filter(translations__field_name)``
