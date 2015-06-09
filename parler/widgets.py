# encoding: utf-8
"""
These widgets perform sorting on the choices within Python.
This is useful when sorting is hard to due translated fields, for example:

* the ORM can't sort it.
* the ordering depends on ``ugettext()`` output.
* the model ``__unicode__()`` value depends on translated fields.

Use them like any regular form widget::

    from django import forms
    from parler.widgets import SortedSelect

    class MyModelForm(forms.ModelForm):
        class Meta:
            # Make sure translated choices are sorted.
            model = MyModel
            widgets = {
                'preferred_language': SortedSelect,
                'country': SortedSelect,
            }

"""
import copy
from django import forms
from django.utils.encoding import force_text
from django.utils.text import slugify

__all__ = (
    'SortedSelect',
    'SortedSelectMultiple',
    'SortedCheckboxSelectMultiple',
)


class SortedChoiceIterator(object):
    def __init__(self, field):
        self.field = field

    def __iter__(self):
        # Delay sorting until the choices are actually read.
        if not self.field._sorted:
            self.field._choices = self.field.sort_choices(self.field._choices)
            self.field._sorted = True
        return iter(self.field._choices)


class SortedSelectMixin(object):
    """
    A mixin to have the choices sorted by (translated) title.
    """
    def __init__(self, attrs=None, choices=()):
        super(SortedSelectMixin, self).__init__(attrs, choices=())
        self._choices = choices   # super may set self.choices=()
        self._sorted = False

    @property
    def choices(self):
        if not self._sorted:
            # Delay evaluation as late as possible.
            # For the admins with a LocationSelectFormMixin, this property is read too early.
            # The RelatedFieldWidgetWrapper() reads the choices on __init__,
            # before the LocationSelectFormMixin can limit the queryset to the current place/region.
            return SortedChoiceIterator(self)
        return self._choices

    @choices.setter
    def choices(self, choices):
        self._choices = choices
        self._sorted = False

    def sort_choices(self, choices):
        # Also sort optgroups
        made_copy = False

        for i, choice in enumerate(choices):
            if isinstance(choice[1], (list, tuple)):
                # An optgroup to sort!
                if not made_copy:
                    # Avoid thread safety issues with other languages.
                    choices = copy.deepcopy(choices)
                    made_copy = True
                    choice = choices[i]

                choice[1].sort(key=_choicesorter)

        if made_copy:
            # avoid another copy.
            choices.sort(key=_choicesorter)
            return choices
        else:
            return sorted(choices, key=_choicesorter)

def _choicesorter(choice):
    if not choice[0]:
        # Allow empty choice to be first
        return False
    else:
        # Lowercase to have case insensitive sorting.
        # For country list, normalize the strings (e.g. Österreich / Oman)
        return slugify(force_text(choice[1]))


class SortedSelect(SortedSelectMixin, forms.Select):
    """
    A select box which sorts it's options.
    """
    pass

class SortedSelectMultiple(SortedSelectMixin, forms.SelectMultiple):
    """
    A multiple-select box which sorts it's options.
    """
    pass

class SortedCheckboxSelectMultiple(SortedSelectMixin, forms.CheckboxSelectMultiple):
    """
    A checkbox group with sorted choices.
    """
    pass
