from django.utils.translation import get_language, activate

__all__ = (
    'smart_override',
    'switch_language',
)

class smart_override(object):
    """
    A contextmanager to switch the translation if needed.

    This context manager can be used to switch the Django translations
    to the current object langauge::

        def get_absolute_url(self):
            with smart_override(language):
                return reverse('myobject-details', args=(self.id,))
    """

    def __init__(self, language_code):
        self.language = language_code
        self.old_language = get_language()

    def __enter__(self):
        # Switch both Django language and object language.
        # For example, when using `object.get_absolute_url()`,
        # a i18n_url() may apply, and a translated database field.
        #
        # Be smarter then translation.override(), also avoid unneeded switches.
        if self.language != self.old_language:
            activate(self.language)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.language != self.old_language:
            activate(self.old_language)


class switch_language(object):
    """
    A contextmanager to switch the translation of an object.

    It changes both the translation language, and object language temporary.
    NOTE: when the object is shared between threads, this is not thread-safe.

    This context manager can be used to switch the Django translations
    to the current object langauge::

        def get_absolute_url(self):
            with switch_language(self):
                return reverse('myobject-details', args=(self.id,))

    It can also be used to render objects in a different language::

        with switch_language(object, 'nl'):
            print object.title
    """

    def __init__(self, object, language_code=None):
        self.object = object
        self.language = language_code or object.get_current_language()
        self.old_language = get_language()
        self.old_parler_language = object.get_current_language()

    def __enter__(self):
        # Switch both Django language and object language.
        # For example, when using `object.get_absolute_url()`,
        # a i18n_url() may apply, and a translated database field.
        #
        # Be smarter then translation.override(), also avoid unneeded switches.
        if self.language != self.old_language:
            activate(self.language)
        if self.language != self.old_parler_language:
            self.object.set_current_language(self.language)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.language != self.old_language:
            activate(self.old_language)
        if self.language != self.old_parler_language:
            self.object.set_current_language(self.old_parler_language)
