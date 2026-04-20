"""
Internal DRY functions.
"""

from django.conf import settings
from parler import appsettings
from parler.utils import get_language_title, is_multilingual_project, normalize_language_code


def get_language_parameter(request, query_language_key="language", object=None, default=None):
    """
    Get the language parameter from the current request.
    """
    # This is the same logic as the django-admin uses.
    # The only difference is the origin of the request parameter.
    if not is_multilingual_project():
        # By default, the objects are stored in a single static language.
        # This makes the transition to multilingual easier as well.
        # The default language can operate as fallback language too.
        return default or appsettings.PARLER_LANGUAGES.get_default_language()
    else:
        # In multilingual mode, take the provided language of the request.
        code = request.GET.get(query_language_key)

        if not code:
            # forms: show first tab by default
            code = default or appsettings.PARLER_LANGUAGES.get_first_language()

        return normalize_language_code(code)


def get_language_tabs(request, current_language, available_languages, css_class=None):
    """
    Determine the language tabs to show.
    """
    tabs = TabsList(css_class=css_class)
    get = request.GET.copy()  # QueryDict object
    tab_languages = []

    site_id = getattr(settings, "SITE_ID", None)

    for lang_dict in appsettings.PARLER_LANGUAGES.get(site_id, ()):
        code = lang_dict["code"]
        title = get_language_title(code)
        get["language"] = code
        url = f"?{get.urlencode()}"

        if code == current_language:
            status = "current"
        elif code in available_languages:
            status = "available"
        else:
            status = "empty"

        tabs.append((url, title, code, status))
        tab_languages.append(code)

    # Additional stale translations in the database?
    if appsettings.PARLER_SHOW_EXCLUDED_LANGUAGE_TABS:
        for code in available_languages:
            if code not in tab_languages:
                get["language"] = code
                url = f"?{get.urlencode()}"

                if code == current_language:
                    status = "current"
                else:
                    status = "available"

                tabs.append((url, get_language_title(code), code, status))
    tabs.available_languages = available_languages
    tabs.current_is_translated = current_language in available_languages
    tabs.allow_deletion = len(available_languages) > 1
    return tabs


class TabsList(list):
    def __init__(self, seq=(), css_class=None):
        self.css_class = css_class
        self.current_is_translated = False
        self.allow_deletion = False
        self.available_languages = []
        super().__init__(seq)


def translate_by_deepl(texts, source_language, target_language, auth_key):
    import requests

    if auth_key.lower().endswith(":fx"):
        endpoint = "https://api-free.deepl.com"
    else:
        endpoint = "https://api.deepl.com"

    r = requests.post(
        f"{endpoint}/v2/translate",
        headers={"Authorization": f"DeepL-Auth-Key {auth_key}"},
        data={
            "target_lang": target_language.upper(),
            "source_lang": source_language.upper(),
            "text": texts,
        },
    )
    if r.status_code == 200:
        return r.json()
    else:
        return {}
