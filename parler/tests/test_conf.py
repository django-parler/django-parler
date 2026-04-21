"""
Tests for parler/utils/conf.py
"""
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from parler.utils.conf import LanguagesSetting, add_default_language_settings, get_parler_languages_from_django_cms


class AddDefaultLanguageSettingsTests(TestCase):
    def test_basic_setup(self):
        lang_list = {1: [{"code": "en"}]}
        result = add_default_language_settings(lang_list, code="en", fallbacks=["en"])
        self.assertIsInstance(result, LanguagesSetting)
        self.assertIn("default", result)

    def test_fallback_singular_to_list_conversion(self):
        """'fallback' key in defaults should be converted to 'fallbacks' list."""
        lang_list = {"default": {"fallback": "en"}}
        result = add_default_language_settings(lang_list, code="en")
        self.assertIn("fallbacks", result["default"])
        self.assertNotIn("fallback", result["default"])
        self.assertEqual(result["default"]["fallbacks"], ["en"])

    def test_fallback_in_extra_defaults_converted(self):
        """'fallback' key passed as extra_default should be converted to 'fallbacks'."""
        lang_list = {}
        result = add_default_language_settings(lang_list, code="en", fallback="en")
        self.assertIn("fallbacks", result["default"])
        self.assertNotIn("fallback", result["default"])

    def test_missing_code_defaults_to_parler_default(self):
        """When 'code' not in defaults and not passed, uses PARLER_DEFAULT_LANGUAGE_CODE."""
        lang_list = {}
        result = add_default_language_settings(lang_list)
        self.assertIn("code", result["default"])

    def test_missing_fallbacks_defaults_to_parler_default(self):
        """When 'fallbacks' not in defaults, uses [PARLER_DEFAULT_LANGUAGE_CODE]."""
        lang_list = {"default": {"code": "en"}}
        result = add_default_language_settings(lang_list, code="en")
        self.assertIn("fallbacks", result["default"])

    def test_invalid_default_code_raises(self):
        """Invalid language code in defaults raises ImproperlyConfigured."""
        lang_list = {}
        with self.assertRaises(ImproperlyConfigured):
            add_default_language_settings(lang_list, code="xx-INVALID")

    def test_invalid_site_languages_not_list_raises(self):
        """Non-list site language config raises ImproperlyConfigured."""
        lang_list = {1: "not-a-list", "default": {"code": "en", "fallbacks": ["en"]}}
        with self.assertRaises(ImproperlyConfigured):
            add_default_language_settings(lang_list, code="en", fallbacks=["en"])

    def test_invalid_site_language_code_raises(self):
        """Invalid code in site language list raises ImproperlyConfigured."""
        lang_list = {1: [{"code": "xx-INVALID"}]}
        with self.assertRaises(ImproperlyConfigured):
            add_default_language_settings(lang_list, code="en", fallbacks=["en"])

    def test_valid_site_languages(self):
        lang_list = {1: [{"code": "en"}, {"code": "nl"}]}
        result = add_default_language_settings(lang_list, code="en", fallbacks=["en"])
        # Defaults should be merged into site language dicts
        self.assertEqual(result[1][0]["code"], "en")
        self.assertIn("hide_untranslated", result[1][0])


class LanguagesSettingGetLanguageTests(TestCase):
    def setUp(self):
        self.lang_settings = LanguagesSetting(
            {
                "default": {"code": "en", "fallbacks": ["en"], "hide_untranslated": False},
                1: [
                    {"code": "en", "fallbacks": ["en"], "hide_untranslated": False},
                    {"code": "nl", "fallbacks": ["en"], "hide_untranslated": False},
                    {"code": "fr-be", "fallbacks": ["fr", "en"], "hide_untranslated": False},
                ],
            }
        )

    def test_get_language_by_exact_code(self):
        lang = self.lang_settings.get_language("en", site_id=1)
        self.assertEqual(lang["code"], "en")

    def test_get_language_partial_match(self):
        """fr-ca should match fr-be by prefix."""
        lang = self.lang_settings.get_language("fr-ca", site_id=1)
        self.assertEqual(lang["code"], "fr-be")

    def test_get_language_falls_back_to_default(self):
        """Unknown language returns default."""
        lang = self.lang_settings.get_language("de", site_id=1)
        self.assertEqual(lang["code"], "en")

    def test_get_language_raises_for_none(self):
        from parler.utils.i18n import get_null_language_error

        with self.assertRaises(ValueError):
            self.lang_settings.get_language(None, site_id=1)

    def test_get_language_uses_site_id_from_settings(self):
        with override_settings(SITE_ID=1):
            lang = self.lang_settings.get_language("en")
            self.assertEqual(lang["code"], "en")


class LanguagesSettingGetActiveChoicesTests(TestCase):
    def setUp(self):
        self.lang_settings = LanguagesSetting(
            {
                "default": {"code": "en", "fallbacks": ["en"], "hide_untranslated": False},
                1: [
                    {
                        "code": "en",
                        "fallbacks": ["en"],
                        "hide_untranslated": False,
                    },
                    {
                        "code": "nl",
                        "fallbacks": ["en"],
                        "hide_untranslated": True,
                    },
                ],
            }
        )

    def test_returns_language_and_fallbacks_when_not_hidden(self):
        choices = self.lang_settings.get_active_choices("en", site_id=1)
        self.assertIn("en", choices)

    def test_returns_only_language_when_hide_untranslated(self):
        choices = self.lang_settings.get_active_choices("nl", site_id=1)
        self.assertEqual(choices, ["nl"])

    def test_uses_current_language_when_none(self):
        from django.utils.translation import activate, deactivate

        activate("en")
        try:
            choices = self.lang_settings.get_active_choices(site_id=1)
            self.assertIn("en", choices)
        finally:
            deactivate()


class LanguagesSettingFallbackTests(TestCase):
    def setUp(self):
        self.lang_settings = LanguagesSetting(
            {
                "default": {"code": "en", "fallbacks": ["en"], "hide_untranslated": False},
                1: [
                    {
                        "code": "en",
                        "fallbacks": ["en"],
                        "hide_untranslated": False,
                    },
                    {
                        "code": "nl",
                        "fallbacks": ["en", "de"],
                        "hide_untranslated": False,
                    },
                ],
            }
        )

    def test_get_fallback_languages(self):
        fallbacks = self.lang_settings.get_fallback_languages("nl", site_id=1)
        self.assertIn("en", fallbacks)

    def test_get_fallback_languages_no_fallback(self):
        fallbacks = self.lang_settings.get_fallback_languages("en", site_id=1)
        self.assertEqual(fallbacks, [])

    def test_get_fallback_language(self):
        fb = self.lang_settings.get_fallback_language("nl", site_id=1)
        # Returns last in choices list (excluding current)
        self.assertIsNotNone(fb)

    def test_get_fallback_language_returns_none_when_no_fallback(self):
        fb = self.lang_settings.get_fallback_language("en", site_id=1)
        self.assertIsNone(fb)

    def test_get_default_language(self):
        self.assertEqual(self.lang_settings.get_default_language(), "en")

    def test_get_first_language(self):
        fl = self.lang_settings.get_first_language(site_id=1)
        self.assertEqual(fl, "en")

    def test_get_first_language_fallback_to_default(self):
        """When site_id not in settings, falls back to default."""
        fl = self.lang_settings.get_first_language(site_id=999)
        self.assertEqual(fl, "en")

    def test_get_first_language_no_site_id(self):
        """When site is empty, falls back to default."""
        lang_settings = LanguagesSetting(
            {"default": {"code": "en", "fallbacks": ["en"], "hide_untranslated": False}}
        )
        fl = lang_settings.get_first_language(site_id=1)
        self.assertEqual(fl, "en")


class GetParlerLanguagesFromDjangoCMSTests(TestCase):
    def test_returns_none_for_none_input(self):
        result = get_parler_languages_from_django_cms(None)
        self.assertIsNone(result)

    def test_converts_cms_languages(self):
        cms_languages = {
            "default": {
                "fallbacks": ["en"],
                "redirect_on_fallback": True,
                "hide_untranslated": False,
                "public": True,  # CMS-specific, should be removed
            },
            1: [
                {
                    "code": "en",
                    "name": "English",  # CMS-specific
                    "public": True,  # CMS-specific
                    "fallbacks": ["en"],
                    "hide_untranslated": False,
                }
            ],
        }
        result = get_parler_languages_from_django_cms(cms_languages)
        self.assertIsNotNone(result)
        # CMS-specific keys should be removed from default
        self.assertNotIn("public", result["default"])
        # CMS-specific keys should be removed from site languages
        self.assertNotIn("name", result[1][0])
        self.assertNotIn("public", result[1][0])

    def test_removes_non_integer_non_default_site_ids(self):
        cms_languages = {
            "default": {"fallbacks": ["en"], "hide_untranslated": False},
            1: [{"code": "en", "fallbacks": ["en"], "hide_untranslated": False}],
            "invalid-key": [{"code": "en"}],  # Should be removed
        }
        result = get_parler_languages_from_django_cms(cms_languages)
        self.assertNotIn("invalid-key", result)
        self.assertIn(1, result)
        self.assertIn("default", result)
