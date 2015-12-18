"""
Context managers for temporary switching the language.
"""
from django.utils.translation import get_language, activate

__all__ = (
    'smart_override',
    'switch_language',
)


class smart_override(object):
    """
    This is a smarter version of :func:`translation.override <django.utils.translation.override>`
    which avoids switching the language if there is no change to make.
    This method can be used in place of :func:`translation.override <django.utils.translation.override>`:

    .. code-block:: python

        with smart_override(self.get_current_language()):
            return reverse('myobject-details', args=(self.id,))

    This makes sure that any URLs wrapped in :func:`~django.conf.urls.i18n.i18n_patterns`
    will receive the correct language code prefix.
    When the URL also contains translated fields (e.g. a slug), use :class:`switch_language` instead.
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

    This context manager can be used to switch the Django translations
    to the current object language.
    It can also be used to render objects in a different language:

    .. code-block:: python

        with switch_language(object, 'nl'):
            print object.title

    This is particularly useful for the :func:`~django.db.models.get_absolute_url` function.
    By using this context manager, the object language will be identical to the current Django language.

    .. code-block:: python

        def get_absolute_url(self):
            with switch_language(self):
                return reverse('myobject-details', args=(self.slug,))

    .. note::

       When the object is shared between threads, this is not thread-safe.
       Use :func:`~parler.models.TranslatableModel.safe_translation_getter` instead
       to read the specific field.
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
