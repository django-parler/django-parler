import inspect

from django.template import Library, Node, TemplateSyntaxError
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.translation import get_language

from parler.models import TranslatableModel, TranslationDoesNotExist
from parler.utils.context import smart_override, switch_language

register = Library()


class ObjectLanguageNode(Node):
    def __init__(self, nodelist, object_var, language_var=None):
        self.nodelist = nodelist  # This name is special in the Node baseclass
        self.object_var = object_var
        self.language_var = language_var

    def render(self, context):
        # Read context data
        object = self.object_var.resolve(context)
        new_language = self.language_var.resolve(context) if self.language_var else get_language()
        if not isinstance(object, TranslatableModel):
            raise TemplateSyntaxError(f"Object '{object}' is not an instance of TranslableModel")

        with switch_language(object, new_language):
            # Render contents inside
            output = self.nodelist.render(context)

        return output


@register.tag
def objectlanguage(parser, token):
    """
    Template tag to switch an object language
    Example::

        {% objectlanguage object "en" %}
          {{ object.title }}
        {% endobjectlanguage %}

    A TranslatedObject is not affected by the ``{% language .. %}`` tag
    as it maintains it's own state. This tag temporary switches the object state.

    Note that using this tag is not thread-safe if the object is shared between threads.
    It temporary changes the current language of the object.
    """
    bits = token.split_contents()
    if len(bits) == 2:
        object_var = parser.compile_filter(bits[1])
        language_var = None
    elif len(bits) == 3:
        object_var = parser.compile_filter(bits[1])
        language_var = parser.compile_filter(bits[2])
    else:
        raise TemplateSyntaxError(
            "'%s' takes one argument (object) and has one optional argument (language)" % bits[0]
        )

    nodelist = parser.parse(("endobjectlanguage",))
    parser.delete_first_token()
    return ObjectLanguageNode(nodelist, object_var, language_var)


@register.simple_tag(takes_context=True)
def get_translated_url(context, lang_code, object=None):
    """
    Get the proper URL for this page in a different language.

    Note that this algorithm performs a "best effect" approach to give a proper URL.
    To make sure the proper view URL is returned, add the :class:`~parler.views.ViewUrlMixin` to your view.

    Example, to build a language menu::

        <ul>
            {% for lang_code, title in LANGUAGES %}
                {% get_language_info for lang_code as lang %}
                {% get_translated_url lang_code as tr_url %}
                {% if tr_url %}<li{% if lang_code == LANGUAGE_CODE %} class="is-selected"{% endif %}><a href="{{ tr_url }}" hreflang="{{ lang_code }}">{{ lang.name_local|capfirst }}</a></li>{% endif %}
            {% endfor %}
        </ul>

    Or to inform search engines about the translated pages::

       {% for lang_code, title in LANGUAGES %}
           {% get_translated_url lang_code as tr_url %}
           {% if tr_url %}<link rel="alternate" hreflang="{{ lang_code }}" href="{{ tr_url }}" />{% endif %}
       {% endfor %}

    Note that using this tag is not thread-safe if the object is shared between threads.
    It temporary changes the current language of the view object.

    The query string of the current page is preserved in the translated URL.
    When the ``object`` variable is explicitly provided however, the query string will not be added.
    In such situation, *django-parler* assumes that the object may point to a completely different page,
    hence to query string is added.
    """
    view = context.get("view", None)
    request = context["request"]

    if object is not None:
        # Cannot reliable determine whether the current page is being translated,
        # or the template code provides a custom object to translate.
        # Hence, not passing the querystring of the current page
        qs = ""
    else:
        # Try a few common object variables, the SingleObjectMixin object,
        # The Django CMS "current_page" variable, or the "page" from django-fluent-pages and Mezzanine.
        # This makes this tag work with most CMSes out of the box.
        object = (
            context.get("object", None)
            or context.get("current_page", None)
            or context.get("page", None)
        )

        # Assuming current page, preserve query string filters.
        qs = request.META.get("QUERY_STRING", "")

    try:
        if view is not None:
            # Allow a view to specify what the URL should be.
            # This handles situations where the slug might be translated,
            # and gives you complete control over the results of this template tag.
            get_view_url = getattr(view, "get_view_url", None)
            if get_view_url:
                with smart_override(lang_code):
                    return _url_qs(view.get_view_url(), qs)

            # Now, the "best effort" part starts.
            # See if it's a DetailView that exposes the object.
            if object is None:
                object = getattr(view, "object", None)

        if object is not None and hasattr(object, "get_absolute_url"):
            # There is an object, get the URL in the different language.
            # NOTE: this *assumes* that there is a detail view, not some edit view.
            # In such case, a language menu would redirect a user from the edit page
            # to a detail page; which is still way better a 404 or homepage.
            if isinstance(object, TranslatableModel):
                # Need to handle object URL translations.
                # Just using smart_override() should be enough, as a translated object
                # should use `switch_language(self)` internally before returning an URL.
                # However, it doesn't hurt to help a bit here.
                with switch_language(object, lang_code):
                    return _url_qs(object.get_absolute_url(), qs)
            else:
                # Always switch the language before resolving, so i18n_patterns() are supported.
                with smart_override(lang_code):
                    return _url_qs(object.get_absolute_url(), qs)
    except TranslationDoesNotExist:
        # Typically projects have a fallback language, so even unknown languages will return something.
        # This either means fallbacks are disabled, or the fallback language is not found!
        return ""

    # Just reverse the current URL again in a new language, and see where we end up.
    # This doesn't handle translated slugs, but will resolve to the proper view name.
    resolver_match = request.resolver_match
    if resolver_match is None:
        # Can't resolve the page itself, the page is apparently a 404.
        # This can also happen for the homepage in an i18n_patterns situation.
        return ""

    with smart_override(lang_code):
        clean_kwargs = _cleanup_urlpattern_kwargs(resolver_match.kwargs)
        return _url_qs(
            reverse(
                resolver_match.view_name,
                args=resolver_match.args,
                kwargs=clean_kwargs,
                current_app=resolver_match.app_name,
            ),
            qs,
        )


def _url_qs(url, qs):
    if qs and "?" not in url:
        return f"{force_str(url)}?{force_str(qs)}"
    else:
        return force_str(url)


@register.filter
def get_translated_field(object, field):
    """
    Fetch a translated field in a thread-safe way, using the current language.
    Example::

        {% language 'en' %}{{ object|get_translated_field:'name' }}{% endlanguage %}
    """
    return object.safe_translation_getter(field, language_code=get_language())


def _cleanup_urlpattern_kwargs(kwargs):
    # For old function-based views, the url kwargs can pass extra arguments to the view.
    # Although these arguments don't have to be passed back to reverse(),
    # it's not a problem because the reverse() function just ignores them as there is no match.
    # However, for class values, an exception occurs because reverse() wants to force_text() them.
    # Hence, remove the kwargs to avoid internal server errors on some exotic views.
    return {k: v for k, v in kwargs.items() if not inspect.isclass(v)}
