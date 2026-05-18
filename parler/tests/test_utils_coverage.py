"""
Coverage gap tests for parler/utils/i18n.py, parler/utils/views.py, and parler/utils/template.py.
"""
from django.test import RequestFactory
from django.utils.translation import override

from parler.utils.conf import add_default_language_settings
from parler.utils.i18n import get_language_title, get_null_language_error, normalize_language_code
from parler.utils.template import select_template_name
from parler.utils.views import get_language_parameter, get_language_tabs

from .utils import AppTestCase, override_parler_settings


# ---------------------------------------------------------------------------
# parler/utils/i18n.py
# ---------------------------------------------------------------------------


class NormalizeLanguageCodeTests(AppTestCase):
    """Tests for normalize_language_code (lines 27-34)."""

    def test_returns_none_for_none_input(self):
        """Returns None when called with None (line 32)."""
        result = normalize_language_code(None)
        self.assertIsNone(result)


class GetLanguageTitleTests(AppTestCase):
    """Tests for get_language_title (lines 45-74)."""

    def test_raises_value_error_for_empty_string(self):
        """Raises ValueError for an empty language code (line 55)."""
        with self.assertRaises(ValueError):
            get_language_title("")

    def test_uses_all_languages_dict_when_show_excluded_tabs_enabled(self):
        """Uses ALL_LANGUAGES_DICT lookup when PARLER_SHOW_EXCLUDED_LANGUAGE_TABS=True (line 60)."""
        with override_parler_settings(PARLER_SHOW_EXCLUDED_LANGUAGE_TABS=True):
            result = get_language_title("en")
        self.assertIsNotNone(result)
        self.assertNotEqual(str(result), "")

    def test_region_variant_falls_back_to_base_language(self):
        """Returns the base-language title for an unsupported region variant (line 72)."""
        # "nl-be" is not in LANGUAGES_DICT; "nl" IS → should return lazy "Dutch"
        result = get_language_title("nl-be")
        self.assertIsNotNone(result)
        # Force evaluation of the lazy string
        result_str = str(result)
        self.assertNotEqual(result_str, "")
        self.assertNotEqual(result_str, "nl-be")  # Did not fall through to returning the raw code


class GetNullLanguageErrorTests(AppTestCase):
    """Tests for get_null_language_error (lines 113-120)."""

    def test_returns_detailed_message_when_no_language_active(self):
        """Returns the management-command hint message when get_language() is None (line 118)."""
        with override_parler_settings(PARLER_DEFAULT_ACTIVATE=False):
            with override(None):
                result = get_null_language_error()
        self.assertIn("language_code can't be null", result)
        self.assertIn("translation.activate", result)


# ---------------------------------------------------------------------------
# parler/utils/views.py
# ---------------------------------------------------------------------------


class GetLanguageParameterTests(AppTestCase):
    """Tests for get_language_parameter (lines 11-30)."""

    def test_returns_default_language_for_non_multilingual_project(self):
        """Returns default language when is_multilingual_project() is False (line 21)."""
        # Override PARLER_LANGUAGES to a dict with no site key so the project
        # appears non-multilingual (SITE_ID=4 will not be found in the dict).
        no_site_langs = add_default_language_settings(
            {"default": {"code": "en", "fallbacks": ["en"]}}
        )
        with override_parler_settings(
            PARLER_LANGUAGES=no_site_langs,
            PARLER_SHOW_EXCLUDED_LANGUAGE_TABS=False,
        ):
            request = RequestFactory().get("/")
            result = get_language_parameter(request)
        self.assertEqual(result, "en")


class GetLanguageTabsExcludedTests(AppTestCase):
    """Tests for get_language_tabs excluded-language block (lines 59-70)."""

    def test_excluded_language_matching_current_gets_current_status(self):
        """An excluded language equal to current_language gets status='current' (line 65)."""
        request = RequestFactory().get("/")
        # Site 4 has nl/de/en; "fr" is not in tab_languages.
        # current_language="fr" → excluded "fr" matches current → status "current"
        with override_parler_settings(PARLER_SHOW_EXCLUDED_LANGUAGE_TABS=True):
            tabs = get_language_tabs(
                request,
                current_language="fr",
                available_languages=["fr"],
            )
        statuses = {tab[2]: tab[3] for tab in tabs}
        self.assertEqual(statuses.get("fr"), "current")

    def test_excluded_language_not_matching_current_gets_available_status(self):
        """An excluded language that is not current gets status='available' (line 67)."""
        request = RequestFactory().get("/")
        # Site 4 has nl/de/en; "fr" is not in tab_languages.
        # current_language="nl", available has "fr" → excluded "fr" ≠ current → status "available"
        with override_parler_settings(PARLER_SHOW_EXCLUDED_LANGUAGE_TABS=True):
            tabs = get_language_tabs(
                request,
                current_language="nl",
                available_languages=["nl", "fr"],
            )
        statuses = {tab[2]: tab[3] for tab in tabs}
        self.assertEqual(statuses.get("fr"), "available")


# ---------------------------------------------------------------------------
# parler/utils/template.py
# ---------------------------------------------------------------------------


class SelectTemplateNameTests(AppTestCase):
    """Tests for select_template_name (lines 7-28)."""

    def test_list_input_converted_to_tuple_and_none_returned_when_no_match(self):
        """A list input is converted to tuple (line 12) and None is returned when no template exists (line 28)."""
        result = select_template_name(["absolutely_nonexistent_parler_test_abc123.html"])
        self.assertIsNone(result)
