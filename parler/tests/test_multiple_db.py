from pprint import pprint

from django.core.cache import cache
from django.test import override_settings
from django.db import connections, ProgrammingError
from django.utils import translation
from .testapp.models import SimpleModel
from .utils import AppTestCase, override_parler_settings
from ..utils.conf import add_default_language_settings


# forcing DEBUG to True is required to have the SQL statement traced to the console for investigation
# (provided the LOGGING setting is configured in runtest.py, see note there).
# @override_settings(DEBUG=True)
class MultipleDbTest(AppTestCase):
    """
    Test model construction and retrieval in non-default database. Most tests are run twice: with and without
    translation cache. When this test set was first added to v2.3, the following tests failed:
        test_save_retrieve_en_translations_with_cache
        test_safe_getter_with_cache
        test_fall_back_translation_untranslated_not_hidden_with_cache
        Any attempt to retrieve a model from one DB and save to another, with or without cache:

        test_duplicate_into_other_db_with_cache
        test_duplicate_into_other_db_no_cache
        test_duplicate_within_same_db_with_cache
        test_duplicate_within_same_db_no_cache

        test_save_preconditions

    First group of failures was traced back to translation cache management: since it is common to all
    databases,  cache acquired in one DB is used in the other, with the expected disasters (see doc on
    Caching.rst and caching_design.rst).

    The second group of failures kept happening after fixing the cache overlap, and also happen
    when caching is disabled. It appeared because of the models local caches (model._translations_cache)
    which are explored, found and not modified: they should have been forcibly saved because of the change
    of database.
    A specific handling of save() when it involves duplicating the model has been added.

    Finally, when saving after changing pk to the pk of another existing model, data sometimes ended
    corrupted in the database with models missing or sharing translations.
    This was "fixed" by raising an exception when detecting this particular condition.

    """
    databases = {"default", "other_db_1", "other_db_2"}

    A_COMMON_PK = 123
    A_TRANS_EN_DEFAULT = "Object A translation_en_default"
    A_TRANS_EN_OTHER_DB_1 = "Object A translation_en_other_db_1"
    A_TRANS_EN_OTHER_DB_2 = "Object A translation_en_other_db_2"
    A_TRANS_FR_DEFAULT = "Object A translation_fr_default"
    A_TRANS_FR_OTHER_DB_1 = "Object A translation_fr_other_db_1"
    A_TRANS_FR_OTHER_DB_2 = "Object A translation_fr_other_db_2"

    B_COMMON_PK = 456
    B_TRANS_FR_DEFAULT = "Object B translation_fr_default"
    B_TRANS_FR_OTHER_DB_1 = "Object B translation_fr_other_db_1"
    B_TRANS_FR_OTHER_DB_2 = "Object B translation_fr_other_db_2"

    C_PK = 789
    C_TRANS_FR = "Object C translation_fr"
    C_TRANS_EN = "Object C translation_en"

    @classmethod
    def setUpTestData(cls):
        """ Create objects with save(using="..."), result is checked  by first test.
            a) Object A in 3 DB, same pk A_COMMON_PK in the 3 databases, with EN and FR
               translations.
            b) Object B in 3 DB, same pk, B_COMMON_PK, translation in FR only (no fallback)
            c) Object C, in other_db_1 only, with translations in EN and FR
            NB: 1) The database is empty, so pk conflicts are not possible.
                2) Saving an instance saves ALL translations.
        """
        # cls.print_db_content("Before setUpData()")
        with translation.override('en'):
            obj_a = SimpleModel(pk=cls.A_COMMON_PK, tr_title=cls.A_TRANS_EN_DEFAULT)
        obj_a.set_current_language('fr')
        obj_a.tr_title = cls.A_TRANS_FR_DEFAULT
        obj_a.save()

        obj_a.set_current_language('en')
        obj_a.tr_title = cls.A_TRANS_EN_OTHER_DB_1
        obj_a.set_current_language('fr')
        obj_a.tr_title = cls.A_TRANS_FR_OTHER_DB_1
        obj_a.save(using="other_db_1")

        obj_a.set_current_language('en')
        obj_a.tr_title = cls.A_TRANS_EN_OTHER_DB_2
        obj_a.set_current_language('fr')
        obj_a.tr_title = cls.A_TRANS_FR_OTHER_DB_2
        obj_a.save(using="other_db_2")

        # cls.print_db_content("After configuring 'en' + 'fr' for obj A in 3 db.")

        with translation.override('fr'):
            obj_b = SimpleModel(pk=cls.B_COMMON_PK, tr_title=cls.B_TRANS_FR_DEFAULT)
            obj_b.save()
            obj_b.tr_title = cls.B_TRANS_FR_OTHER_DB_1
            obj_b.save(using="other_db_1")
            obj_b.tr_title = cls.B_TRANS_FR_OTHER_DB_2
            obj_b.save(using="other_db_2")
            # cls.print_db_content("After configuring 'FR' for obj B")

        obj_c = SimpleModel(pk=cls.C_PK, tr_title=cls.C_TRANS_EN)
        obj_c.save(using='other_db_1')
        obj_c.set_current_language('fr')
        obj_c.tr_title = cls.C_TRANS_FR
        obj_c.save()
        # cls.print_db_content("After setUpTestData()")

    @classmethod
    def print_db_content(cls, label: str):
        """ Print the raw content of the simple_objects and translations tables,
            for diagnostic.
            :param label: A string to print as title to identify the significance of the dump. """
        print(f"{label}: content of databases:")
        for alias in ("default", "other_db_1", "other_db_2"):
            print(f"--------- Database: '{alias}' ------------")
            with connections[alias].cursor() as cursor:
                for table in (SimpleModel._meta.db_table, SimpleModel._meta.db_table + "_translation"):
                    print(f"    Table '{table}':")
                    cursor.execute(f"SELECT * FROM {table}")  # noqa

                    for row in cursor.fetchall():
                        print("    ", end='')
                        pprint(row)
        print("--------------------------------")

    @classmethod
    def get_num_translations(cls, pk: int | None, using: str) -> int:
        """ Count how many translation rows exist in database with provided alias,
            for SimpleModel with given pk.
            :param pk: The id of the SimpleModel instance to consider. if None, all translations are counted.
            :param using: The database alias to use.
        """
        with connections[using].cursor() as cursor:
            table = SimpleModel._meta.db_table + "_translation"
            if pk is not None:
                where_clause = f" WHERE master_id={pk}"
            else:
                where_clause = ""
            cursor.execute(f"SELECT COUNT(*) from {table} {where_clause}")
            return cursor.fetchone()[0]

    def setUp(self):
        """ Clear the translation cache before each test to guarantee tests idempotency."""
        cache.clear()

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_save_retrieve_en_translations_no_cache(self):
        self.check_save_retrieve_en_translations()

    def test_save_retrieve_en_translations_with_cache(self):
        self.check_save_retrieve_en_translations()

    def check_save_retrieve_en_translations(self):
        """ Check data installed in setUpData() with all retrieval methods, in English. """
        # Query on pk and check the right translation is retrieved.
        # Query on translation to check objects are found from non default db.
        # 1. default DB.
        # self.print_db_content("before testing")
        # print(f"Current language is '{get_language()}'")
        obj_a = SimpleModel.objects.translated(tr_title=self.A_TRANS_EN_DEFAULT).first()
        self.assertEqual(obj_a.pk, self.A_COMMON_PK)
        obj_a = SimpleModel.objects.get(pk=self.A_COMMON_PK)
        self.assertEqual(obj_a.tr_title, self.A_TRANS_EN_DEFAULT)

        # 2. other DB 1 (with using() BEFORE translated())
        obj_a = SimpleModel.objects.using("other_db_1").translated(tr_title=self.A_TRANS_EN_OTHER_DB_1).first()
        self.assertEqual(obj_a.tr_title, self.A_TRANS_EN_OTHER_DB_1)
        obj_a = SimpleModel.objects.using("other_db_1").get(pk=self.A_COMMON_PK)
        self.assertEqual(obj_a.tr_title, self.A_TRANS_EN_OTHER_DB_1)

        # 3 other DB 2 (with using() AFTER translated())
        obj_a = SimpleModel.objects.translated(tr_title=self.A_TRANS_EN_OTHER_DB_2).using("other_db_2").first()
        self.assertEqual(obj_a.pk, self.A_COMMON_PK)
        obj_a = SimpleModel.objects.using("other_db_2").get(pk=self.A_COMMON_PK)
        self.assertEqual(obj_a.tr_title, self.A_TRANS_EN_OTHER_DB_2)

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_fall_back_translation_untranslated_not_hidden_no_cache(self):
        self.check_fallback_translation_w_existing_fallback_untranslated_not_hidden()

    def test_fall_back_translation_untranslated_not_hidden_with_cache(self):
        self.check_fallback_translation_w_existing_fallback_untranslated_not_hidden()

    def check_fallback_translation_w_existing_fallback_untranslated_not_hidden(self):
        """ Check fallback language is handled properly. Object A has a fallback, en,
            translation and a 'fr' translation.
            NB: hide_untranslated is False (default value) in the settings defined by runtest.py.
        """
        # Fallback should work for obj A
        # self.print_db_content("Before retrieving object A in 'de'")
        with translation.override('de'):
            obj = SimpleModel.objects.using("default"). \
                active_translations(tr_title=self.A_TRANS_EN_DEFAULT).first()
            self.assertEqual(obj.tr_title, self.A_TRANS_EN_DEFAULT, " (default DB)")
            obj = SimpleModel.objects.using("other_db_1"). \
                active_translations(tr_title=self.A_TRANS_EN_OTHER_DB_1).first()
            self.assertEqual(obj.tr_title, self.A_TRANS_EN_OTHER_DB_1, " (other_db_1)")
            obj = SimpleModel.objects.using("other_db_2") \
                .active_translations(tr_title=self.A_TRANS_EN_OTHER_DB_2).first()
            self.assertEqual(obj.tr_title, self.A_TRANS_EN_OTHER_DB_2, " (other_db_2)")

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_fallback_translation_w_existing_fallback_untranslated_hidden_no_cache(self):
        self.check_fallback_translation_w_existing_fallback_untranslated_hidden()

    def test_fallback_translation_w_existing_fallback_untranslated_hidden_with_cache(self):
        self.check_fallback_translation_w_existing_fallback_untranslated_hidden()

    @override_parler_settings(PARLER_LANGUAGES=add_default_language_settings({
        4: (
                {"code": "nl"},
                {"code": "de"},
                {"code": "en"},
        ),
        "default": {
            "fallbacks": ["en"],
            "hide_untranslated": False,
        }
    })
    )
    def check_fallback_translation_w_existing_fallback_untranslated_hidden(self):
        """ Check fallback language is handled properly (object A has a fallback, en,
            translation and a 'fr' translation): nothing should be found because of the missing
            translation.
            NB: hide_untranslated is False (default value) in the settings defined by runtest.py.
        """
        # Fallback should work for obj A
        with translation.override('de'):
            num_found = SimpleModel.objects.using("default") \
                .active_translations(tr_title=self.A_TRANS_EN_DEFAULT).count()
            self.assertEqual(num_found, 1, " (default db)")
            num_found = SimpleModel.objects.using("other_db_1") \
                .active_translations(tr_title=self.A_TRANS_EN_OTHER_DB_1).count()
            self.assertEqual(num_found, 1, " (default db)")
            num_found = SimpleModel.objects.using("other_db_2") \
                .active_translations(tr_title=self.A_TRANS_EN_OTHER_DB_2).count()
            self.assertEqual(num_found, 1, " (default db)")

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_fall_back_translation_no_fallback_no_cache(self):
        self.check_fall_back_translation_no_fallback()

    def test_fall_back_translation_no_fallback_with_cache(self):
        self.check_fall_back_translation_no_fallback()

    def check_fall_back_translation_no_fallback(self):
        """ Object B does not have any 'en' translation, just a fr
            translation. """
        # Fallback should fail for obj B
        with translation.override('de'):
            num_found = SimpleModel.objects.using("default") \
                .active_translations(tr_title=self.B_TRANS_FR_DEFAULT).count()
            self.assertEqual(num_found, 0, " (default db)")
            num_found = SimpleModel.objects.using("other_db_1") \
                .active_translations(tr_title=self.B_TRANS_FR_OTHER_DB_1).count()
            self.assertEqual(num_found, 0, " (other_db_1)")
            num_found = SimpleModel.objects.using("other_db_2") \
                .active_translations(tr_title=self.B_TRANS_FR_OTHER_DB_2).count()
            self.assertEqual(num_found, 0, " (other_db_2)")

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_safe_getter_no_cache(self):
        self.check_safe_getter()

    def test_safe_getter_with_cache(self):
        self.check_safe_getter()

    def check_safe_getter(self):
        obj = SimpleModel.objects.using("other_db_1").get(pk=self.A_COMMON_PK)
        title_fr = obj.safe_translation_getter('tr_title', language_code='fr')
        self.assertEqual(title_fr, self.A_TRANS_FR_OTHER_DB_1)
        obj = SimpleModel.objects.using("other_db_2").get(pk=self.A_COMMON_PK)
        title_fr = obj.safe_translation_getter('tr_title', language_code='fr')
        self.assertEqual(title_fr, self.A_TRANS_FR_OTHER_DB_2)

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_update_in_implicit_db_no_cache(self):
        self.check_update_in_implicit_db()

    def test_update_in_implicit_db_with_cache(self):
        self.check_update_in_implicit_db()

    def check_update_in_implicit_db(self):
        """ Retrieve from non-default db and save change implicitly in the same base.
            Run this test with cache disabled to make sure the value is actually checked in the db."""
        # self.print_db_content("Before updating object A in other_db_1 with implicit save()")
        obj_1 = SimpleModel.objects.using("other_db_1").get(pk=self.A_COMMON_PK)
        obj_1.tr_title = "changed in other_db_1"
        obj_2 = SimpleModel.objects.using("other_db_2").get(pk=self.A_COMMON_PK)
        obj_2.tr_title = "changed in other_db_2"
        obj_1.save()  # Should save in 'other_db_1'
        obj_2.save()  # Should save in 'other_db_2'
        # self.print_db_content("After updating object A in other_db_1 with implicit save()")

        objs = SimpleModel.objects.using("other_db_1").translated(tr_title="changed in other_db_1")
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].tr_title, "changed in other_db_1")
        objs = SimpleModel.objects.using("other_db_2").translated(tr_title="changed in other_db_2")
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].tr_title, "changed in other_db_2")

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_create_retrieve_no_cache(self):
        self.check_create_retrieve()

    def test_create_retrieve_with_cache(self):
        self.check_create_retrieve()

    def check_create_retrieve(self):
        """ Creating model using objects.create() in non-default database. """
        with translation.override('de'):
            SimpleModel.objects.using("other_db_1").create(tr_title="de_created_in_other_db_1")
            objs = SimpleModel.objects.translated(tr_title="de_created_in_other_db_1").using('other_db_1')
            self.assertEqual(len(objs), 1)
            self.assertEqual(objs[0].tr_title, "de_created_in_other_db_1")

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_duplicate_into_other_db_no_cache(self):
        self.check_duplicate_into_other_db()

    def test_duplicate_into_other_db_with_cache(self):
        self.check_duplicate_into_other_db()

    def check_duplicate_into_other_db(self):
        """ Retrieve model from one DB and save in another one. All translations should be saved,
            and unsaved changes should be saved as well.
        """
        with translation.override('fr'):
            # retrieve object C with FR translation from other_db_1
            # self.print_db_content(f"Before retrieving obj C (pk={self.C_PK}) in FR from other_db_1")
            obj = SimpleModel.objects.using('other_db_1').get(pk=self.C_PK)
            obj.tr_title += "_CHANGE_1"

            # Do not clear PK for duplication (but it will be regenerated in new DB).
            original_num_translations_db_2 = self.get_num_translations(None, 'other_db_2')
            obj._duplicate(using='other_db_2')
            # self.print_db_content(f"After duplicating obj C (pk={self.C_PK}) into other_db_2")
            self.assertEqual(obj._state.db, 'other_db_2')
            self.assertNotEquals(obj.pk, self.C_PK)

            retrieved_obj = SimpleModel.objects.using('other_db_2').get(pk=obj.pk)
            self.assertEqual(self.get_num_translations(obj.pk, 'other_db_2'),
                             2, "Object should have found two translations")
            self.assertEqual(self.get_num_translations(None, 'other_db_2'),
                             original_num_translations_db_2 + 2, "Should have found two extra translations")
            self.assertEqual(retrieved_obj.tr_title, self.C_TRANS_FR + "_CHANGE_1")

            # Modify duplicated object and check it is modified in 'other_db_2'
            obj.tr_title += "_CHANGE_2"
            obj.save()
            retrieved_obj = SimpleModel.objects.using('other_db_2').get(pk=obj.pk)
            self.assertEqual(retrieved_obj.tr_title, self.C_TRANS_FR + "_CHANGE_1_CHANGE_2")
            # self.print_db_content(f"After changing/saving dupl object")

            # Check original object is still unchanged, as expected
            original_obj = SimpleModel.objects.using('other_db_1').get(pk=self.C_PK)
            self.assertEqual(original_obj.tr_title, self.C_TRANS_FR)

    @override_parler_settings(PARLER_ENABLE_CACHING=False)
    def test_duplicate_within_same_db_no_cache(self):
        self.check_duplicate_within_same_db()

    def test_duplicate_within_same_db_with_cache(self):
        self.check_duplicate_within_same_db()

    def check_duplicate_within_same_db(self):
        """ Retrieve model from DB and _duplicate it in the same database. All translations should be saved,
            and unsaved changes should be saved as well.
        """
        with translation.override('fr'):
            # retrieve object C with FR translation from other_db_1
            # self.print_db_content(f"Before retrieving obj C (pk={self.C_PK}) in FR from other_db_1")
            obj = SimpleModel.objects.using('other_db_1').get(pk=self.C_PK)
            obj.tr_title += "_CHANGE_1"

            # clear PK to force duplication
            obj.pk = None
            original_num_translations_db_1 = self.get_num_translations(None, 'other_db_1')
            obj.save()
            # self.print_db_content(f"After duplicating obj C (pk={self.C_PK}) into other_db_2")
            self.assertEqual(obj._state.db, 'other_db_1')
            self.assertNotEquals(obj.pk, self.C_PK)

            retrieved_obj = SimpleModel.objects.using('other_db_1').get(pk=obj.pk)
            self.assertEqual(self.get_num_translations(obj.pk, 'other_db_1'),
                             2, "Object should have found two translations")
            self.assertEqual(self.get_num_translations(None, 'other_db_1'),
                             original_num_translations_db_1 + 2, "Should have found two extra translations")
            self.assertEqual(retrieved_obj.tr_title, self.C_TRANS_FR + "_CHANGE_1")

            # Modify duplicated object and check it is modified in 'other_db_2'
            obj.tr_title += "_CHANGE_2"
            obj.save()
            retrieved_obj = SimpleModel.objects.using('other_db_1').get(pk=obj.pk)
            self.assertEqual(retrieved_obj.tr_title, self.C_TRANS_FR + "_CHANGE_1_CHANGE_2")
            # self.print_db_content(f"After changing/saving dupl object")

            # Check original object is still unchanged, as expected
            original_obj = SimpleModel.objects.using('other_db_1').get(pk=self.C_PK)
            self.assertEqual(original_obj.tr_title, self.C_TRANS_FR)

    def test_duplicate_precondition(self):
        """ Test exception is raised when calling _duplicate() with never-saved object """

        obj = SimpleModel(tr_title="xxx")
        with self.assertRaises(ProgrammingError):
            obj._duplicate()

    def test_save_preconditions(self):
        """ Test exceptions are raised when calling save() in unsupported configurations """

        # Try to save new model in same DB with pk not in use (should work)
        obj = SimpleModel(tr_title='abc')
        obj.pk = self.C_PK + 10000
        obj.save()

        # Try to save in same DB with pk not in use (should work)
        obj.pk = self.C_PK + 10001
        obj.save()

        # Try to save in other DB with pk not in use (should work)
        obj.pk = self.C_PK + 10001
        obj.save(using="other_db_2")

        # Try to save in other db with existing pk to overwrite model.
        obj.pk = self.C_PK + 10001
        with self.assertRaises(NotImplementedError):
            obj.save(using="default")

        # Try to save new model with existing pk to overwrite model.
        obj = SimpleModel(tr_title="xxx")
        obj.pk = self.C_PK
        with self.assertRaises(NotImplementedError):
            obj.save(using="other_db_1")

    def test_delete_from_explicit_db(self):
        """ Delete object specifying database in delete().
            All translations should be deleted with the object. """
        obj = SimpleModel.objects.using('other_db_1').get(pk=self.C_PK)
        obj.delete(using="other_db_1")
        self.assertEqual(self.get_num_translations(self.C_PK, 'other_db_1'),
                         0, "Should have deleted all translations")

    def test_delete_from_implicit_db(self):
        """ Delete object without specifying database in delete().
            All translations should be deleted with the object. """
        obj = SimpleModel.objects.using('other_db_1').get(pk=self.C_PK)
        obj.delete()
        self.assertEqual(self.get_num_translations(self.C_PK, 'other_db_1'),
                         0, "Should have deleted all translations")

    # NB: Exposing multi-db models in Admin only relies on a custom ModelAdmin that
    #     makes use of the "using" features tested above.
