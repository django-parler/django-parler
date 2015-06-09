from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils import six

_cached_name_lookups = {}


def select_template_name(template_name_list):
    """
    Given a list of template names, find the first one that exists.
    """
    if not isinstance(template_name_list, tuple):
        template_name_list = tuple(template_name_list)

    try:
        return _cached_name_lookups[template_name_list]
    except KeyError:
        # Find which template of the template_names is selected by the Django loader.
        for template_name in template_name_list:
            try:
                # TODO: For Django 1.8, add using= parameter so it only selects templates from the same engine.
                get_template(template_name)
            except TemplateDoesNotExist:
                continue
            else:
                template_name = six.text_type(template_name)  # consistent value for lazy() function.
                _cached_name_lookups[template_name_list] = template_name
                return template_name

        return None
