"""
Internal DRY functions.
"""
from django.conf import settings
from parler import appsettings
from parler.utils import normalize_language_code, is_multilingual_project, get_language_title


def get_language_parameter(request, query_language_key='language', object=None, default=None):
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

    base_url = '{0}://{1}{2}'.format(request.is_secure() and 'https' or 'http', request.get_host(), request.path)

    site_id = getattr(settings, 'SITE_ID', None)
    for lang_dict in appsettings.PARLER_LANGUAGES.get(site_id, ()):
        code = lang_dict['code']
        title = get_language_title(code)
        get['language'] = code
        url = '{0}?{1}'.format(base_url, get.urlencode())

        if code == current_language:
            status = 'current'
        elif code in available_languages:
            status = 'available'
        else:
            status = 'empty'

        tabs.append((url, title, code, status))
        tab_languages.append(code)

    # Additional stale translations in the database?
    if appsettings.PARLER_SHOW_EXCLUDED_LANGUAGE_TABS:
        for code in available_languages:
            if code not in tab_languages:
                get['language'] = code
                url = '{0}?{1}'.format(base_url, get.urlencode())

                if code == current_language:
                    status = 'current'
                else:
                    status = 'available'

                tabs.append((url, get_language_title(code), code, status))

    tabs.current_is_translated = current_language in available_languages
    tabs.allow_deletion = len(available_languages) > 1
    return tabs


class TabsList(list):
    def __init__(self, seq=(), css_class=None):
        self.css_class = css_class
        self.current_is_translated = False
        self.allow_deletion = False
        super(TabsList, self).__init__(seq)
