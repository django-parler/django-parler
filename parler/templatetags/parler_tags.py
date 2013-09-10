from django.template import Node, Library, TemplateSyntaxError
from django.utils.translation import get_language
from parler.models import TranslatableModel

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
            raise TemplateSyntaxError("Object '{0}' is not an instance of TranslableModel".format(object))

        # Switch
        old_object_language = object.get_current_language()
        object.set_current_language(new_language)

        try:
            # Render contents inside
            output = self.nodelist.render(context)
        finally:
            # Switch back and return
            object.set_current_language(old_object_language)

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

    If the global language needs to be switched too,
    wrap this tag in a ``{% language %}`` block.
    """
    bits = token.split_contents()
    if len(bits) == 2:
        object_var = parser.compile_filter(bits[1])
        language_var = None
    elif len(bits) == 3:
        object_var = parser.compile_filter(bits[1])
        language_var = parser.compile_filter(bits[2])
    else:
        raise TemplateSyntaxError("'%s' takes one argument (object) and has one optional argument (language)" % bits[0])

    nodelist = parser.parse(('endobjectlanguage',))
    parser.delete_first_token()
    return ObjectLanguageNode(nodelist, object_var, language_var)
