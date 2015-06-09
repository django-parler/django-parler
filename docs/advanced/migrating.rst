Making existing fields translatable
===================================

The following guide explains how to make existing fields translatable,
and migrate the data from the old fields to translated fields.

*django-parler* stores translated fields in a separate model,
so it can store multiple versions (translations) of the same field.
To make existing fields translatable, 3 migration steps are needed:

1. Create the translation table, keep the existing columns
2. Copy the data from the original table to the translation table.
3. Remove the fields from the original model.

The following sections explain this in detail:

Step 1: Create the translation table
------------------------------------

Say we have the following model::

    class MyModel(models.Model):
        name = models.CharField(max_length=123)


First create the translatable fields::

    class MyModel(TranslatableModel):
        name = models.CharField(max_length=123)

        translations = TranslatedFields(
              name=models.CharField(max_length=123),
        )

Now create the migration:

* For Django 1.7, use: ``manage.py makemigrations myapp  "add_translation_model"``
* For South, use:  ``manage.py schemamigration myapp --auto "add_translation_model"``


Step 2: Copy the data
---------------------

Within the data migration, copy the existing data:

Using Django
~~~~~~~~~~~~

Create an empty migration::

    manage.py makemigrations --empty myapp "migrate_translatable_fields"

And use it to move the data::

    def forwards_func(apps, schema_editor):
        MyModel = apps.get_model('myapp', 'MyModel')
        MyModelTranslation = apps.get_model('myapp', 'MyModelTranslation')

        for object in MyModel.objects.all():
            MyModelTranslation.objects.create(
                master_id=object.pk,
                language_code=settings.LANGUAGE_CODE,
                name=object.name
            )

    def backwards_func(apps, schema_editor):
        MyModel = apps.get_model('myapp', 'MyModel')
        MyModelTranslation = apps.get_model('myapp', 'MyModelTranslation')

        for object in MyModel.objects.all():
            translation = _get_translation(object, MyModelTranslation)
            object.name = translation.name
            object.save()   # Note this only calls Model.save() in South.

    def _get_translation(object, MyModelTranslation):
        translations = MyModelTranslation.objects.filter(master_id=object.pk)
        try:
            # Try default translation
            return translations.get(language_code=settings.LANGUAGE_CODE)
        except ObjectDoesNotExist:
            try:
                # Try default language
                return translations.get(language_code=settings.PARLER_DEFAULT_LANGUAGE_CODE)
            except ObjectDoesNotExist:
                # Maybe the object was translated only in a specific language?
                # Hope there is a single translation
                return translations.get()


    class Migration(migrations.Migration):

        dependencies = [
            ('yourappname', '0001_initial'),
        ]

        operations = [
            migrations.RunPython(forwards_func, backwards_func),
        ]

.. note::
   Be careful which language is used to migrate the existing data.
   In this example, the ``backwards_func()`` logic is extremely defensive not to loose translated data.


Using South
~~~~~~~~~~~

With South, create a data migration::

    manage.py datamigration myapp "migrate_translatable_fields"

The logic is identical, only the way for receiving the ORM models differs::

    class Migration(DataMigration):

        def forwards(self, orm):
            MyModel = orm['myapp.MyModel']
            MyModelTranslation = orm['myapp.MyModelTranslation']

            for object in MyModel.objects.all():
                MyModelTranslation.objects.create(
                    master_id=object.pk,
                    language_code=settings.LANGUAGE_CODE,
                    name=object.name
                )

        def backwards(self, orm):
            # Convert all fields back to the single-language table.
            MyModel = orm['myapp.MyModel']
            MyModelTranslation = orm['myapp.MyModelTranslation']

            for object in MyModel.objects.all():
                translation = _get_translation(object, MyModelTranslation)
                object.name = translation.name
                object.save()   # Note this only calls Model.save() in South.


    def _get_translation(object, MyModelTranslation):
        translations = MyModelTranslation.objects.filter(master_id=object.pk)
        try:
            # Try default translation
            return translations.get(language_code=settings.LANGUAGE_CODE)
        except ObjectDoesNotExist:
            try:
                # Try default language
                return translations.get(language_code=settings.PARLER_DEFAULT_LANGUAGE_CODE)
            except ObjectDoesNotExist:
                # Maybe the object was translated only in a specific language?
                # Hope there is a single translation
                return translations.get()

The forwards method can also be implemented in raw SQL::

    class Migration(DataMigration):

        def forwards(self, orm):
            db.execute(
                'INSERT INTO myapp_mymodel_translation(name, language_code, master_id)'
                ' SELECT name, _cached_url, %s, id FROM myapp_mymodel',
                [settings.LANGUAGE_CODE]
            )

.. note::
   Be careful which language is used to migrate the existing data.
   In this example, the ``backwards()`` logic is extremely defensive not to loose translated data.


Step 3: Remove the old fields
-----------------------------

Remove the old field from the original model.
The example model now looks like::

    class MyModel(TranslatableModel):
        translations = TranslatedFields(
            name=models.CharField(max_length=123),
        )

Create the database migration, it will simply remove the original field.

* For Django 1.7, use: ``manage.py makemigrations myapp  "remove_untranslated_fields"``
* For South, use:  ``manage.py schemamigration myapp --auto "remove_untranslated_fields"``


Updating code
-------------

The project code should be updated. For example:

* Replace ``filter(field_name)`` with ``.translated(field_name)`` or ``filter(translations__field_name)``.
* Make sure there is one filter on the translated fields, see :ref:`orm-restrictions`.
* Update the ``ordering`` and ``order_by()`` code. See :ref:`ordering`.
* Update the admin ``search_fields`` and ``prepopulated_fields``. See :ref:`admin-compat`.


Deployment
----------

To have a smooth deployment, it's recommended to only run the first 2 migrations
- which create columns and move the data.
Removing the old fields should be done after reloading the WSGI instance.
