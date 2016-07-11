from django import forms
import django
from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS, ObjectDoesNotExist, ValidationError
from django.forms.forms import BoundField
from django.forms.models import ModelFormMetaclass, BaseInlineFormSet
from django.utils.functional import cached_property
from django.utils.translation import get_language
from django.utils import six
from parler.models import TranslationDoesNotExist
from parler.utils import compat


__all__ = (
    'TranslatableModelForm',
    'TranslatedField',
    'BaseTranslatableModelForm',
    #'TranslatableModelFormMetaclass',
)


class TranslatedField(object):
    """
    A wrapper for a translated form field.

    This wrapper can be used to declare translated fields on the form, e.g.

    .. code-block:: python

        class MyForm(TranslatableModelForm):
            title = TranslatedField()
            slug = TranslatedField()

            description = TranslatedField(form_class=forms.CharField, widget=TinyMCE)
    """

    def __init__(self, **kwargs):
        # The metaclass performs the magic replacement with the actual formfield.
        self.kwargs = kwargs


class BaseTranslatableModelForm(forms.BaseModelForm):
    """
    The base methods added to :class:`TranslatableModelForm` to fetch and store translated fields.
    """
    language_code = None    # Set by TranslatableAdmin.get_form() on the constructed subclass.

    def __init__(self, *args, **kwargs):
        current_language = kwargs.pop('_current_language', None)   # Used for TranslatableViewMixin
        super(BaseTranslatableModelForm, self).__init__(*args, **kwargs)

        # Load the initial values for the translated fields
        instance = kwargs.get('instance', None)
        if instance:
            for meta in instance._parler_meta:
                try:
                    # By not auto creating a model, any template code that reads the fields
                    # will continue to see one of the other translations.
                    # This also causes admin inlines to show the fallback title in __unicode__.
                    translation = instance._get_translated_model(meta=meta)
                except TranslationDoesNotExist:
                    pass
                else:
                    for field in meta.get_translated_fields():
                        try:
                            self.initial.setdefault(field, getattr(translation, field))
                        except ObjectDoesNotExist:
                            # This occurs when a ForeignKey field is part of the translation,
                            # but it's value is still not yet, and the field has null=False.
                            pass

        # Typically already set by admin
        if self.language_code is None:
            if instance:
                self.language_code = instance.get_current_language()
            else:
                self.language_code = current_language or get_language()

        if self.language_code not in dict(settings.LANGUAGES):
            # Instead of raising a ValidationError
            raise ValueError(
                "Translatable forms can't be initialized for the language '{0}', "
                "that option does not exist in the 'LANGUAGES' setting.".format(self.language_code)
            )

    def _get_translation_validation_exclusions(self, translation):
        exclude = ['master']
        if 'language_code' not in self.fields:
            exclude.append('language_code')

        # This is the same logic as Django's _get_validation_exclusions(),
        # only using the translation model instead of the master instance.
        for field_name in translation.get_translated_fields():
            if field_name not in self.fields:
                # Exclude fields that aren't on the form.
                exclude.append(field_name)
            elif self._meta.fields and field_name not in self._meta.fields:
                # Field might be added manually at the form,
                # but wasn't part of the ModelForm's meta.
                exclude.append(field_name)
            elif self._meta.exclude and field_name in self._meta.exclude:
                # Same for exclude.
                exclude.append(field_name)
            elif field_name in self._errors.keys():
                # No need to validate fields that already failed.
                exclude.append(field_name)
            else:
                # Exclude fields that are not required in the form, while the model requires them.
                # See _get_validation_exclusions() for the detailed bits of this logic.
                form_field = self.fields[field_name]
                model_field = translation._meta.get_field(field_name)
                field_value = self.cleaned_data.get(field_name)
                if not model_field.blank and not form_field.required and field_value in form_field.empty_values:
                    exclude.append(field_name)

        return exclude

    def _post_clean(self):
        # Copy the translated fields into the model
        # Make sure the language code is set as early as possible (so it's active during most clean() methods)
        self.instance.set_current_language(self.language_code)
        self.save_translated_fields()

        # Perform the regular clean checks, this also updates self.instance
        super(BaseTranslatableModelForm, self)._post_clean()

    def save_translated_fields(self):
        """
        Save all translated fields.
        """
        fields = {}

        # Collect all translated fields {'name': 'value'}
        for field in self._translated_fields:
            try:
                value = self.cleaned_data[field]
            except KeyError:  # Field has a ValidationError
                continue
            fields[field] = value

        # Set the field values on their relevant models
        translations = self.instance._set_translated_fields(**fields)

        # Perform full clean on models
        non_translated_fields = set(('id', 'master_id', 'language_code'))
        for translation in translations:
            self._post_clean_translation(translation)

            # Assign translated fields to the model (using the TranslatedAttribute descriptor)
            for field in translation._get_field_names():
                if field in non_translated_fields:
                    continue
                setattr(self.instance, field, getattr(translation, field))

    if django.VERSION >= (1, 6):

        def _post_clean_translation(self, translation):
            exclude = self._get_translation_validation_exclusions(translation)
            try:
                translation.full_clean(
                    exclude=exclude, validate_unique=False)
            except ValidationError as e:
                self._update_errors(e)

            # Validate uniqueness if needed.
            if self._validate_unique:
                try:
                    translation.validate_unique()
                except ValidationError as e:
                    self._update_errors(e)
    else:

        def _post_clean_translation(self, translation):
            exclude = self._get_translation_validation_exclusions(translation)
            # Clean the model instance's fields.
            try:
                translation.clean_fields(exclude=exclude)
            except ValidationError as e:
                self._update_errors(e.message_dict)

            # Call the model instance's clean method.
            try:
                translation.clean()
            except ValidationError as e:
                self._update_errors({NON_FIELD_ERRORS: e.messages})

            # Validate uniqueness if needed.
            if self._validate_unique:
                try:
                    translation.validate_unique()
                except ValidationError as e:
                    self._update_errors(e.message_dict)

    @cached_property
    def _translated_fields(self):
        field_names = self._meta.model._parler_meta.get_all_fields()
        return [f_name for f_name in field_names if f_name in self.fields]

    def __getitem__(self, name):
        """
        Return a :class:`TranslatableBoundField` for translated models.
        This extends the default ``form[field]`` interface that produces the BoundField for HTML templates.
        """
        boundfield = super(BaseTranslatableModelForm, self).__getitem__(name)
        if name in self._translated_fields:
            # Oh the wonders of Python :)
            boundfield.__class__ = _upgrade_boundfield_class(boundfield.__class__)
        return boundfield


UPGRADED_CLASSES = {}


def _upgrade_boundfield_class(cls):
    if cls is BoundField:
        return TranslatableBoundField
    elif issubclass(cls, TranslatableBoundField):
        return cls

    # When some other package also performs this same trick,
    # combine both classes on the fly. Avoid having to do that each time.
    # This is needed for django-slug-preview
    try:
        return UPGRADED_CLASSES[cls]
    except KeyError:
        # Create once
        new_cls = type('Translatable{0}'.format(cls.__name__), (cls, TranslatableBoundField), {})
        UPGRADED_CLASSES[cls] = new_cls
        return new_cls


class TranslatableBoundField(BoundField):
    """
    Decorating the regular BoundField to distinguish translatable fields in the admin.
    """
    #: A tagging attribute, making it easy for templates to identify these fields
    is_translatable = True

    def label_tag(self, contents=None, attrs=None, *args, **kwargs):  # extra args differ per Django version
        if attrs is None:
            attrs = {}

        attrs['class'] = (attrs.get('class', '') + " translatable-field").strip()
        return super(TranslatableBoundField, self).label_tag(contents, attrs, *args, **kwargs)

    # The as_widget() won't be overwritten to add a 'class' attr,
    # because it will overwrite what AdminTextInputWidget and fields have as default.


class TranslatableModelFormMetaclass(ModelFormMetaclass):
    """
    Meta class to add translated form fields to the form.
    """
    def __new__(mcs, name, bases, attrs):
        # Before constructing class, fetch attributes from bases list.
        form_meta = _get_mro_attribute(bases, '_meta')
        form_base_fields = _get_mro_attribute(bases, 'base_fields', {})  # set by previous class level.

        if form_meta:
            # Not declaring the base class itself, this is a subclass.

            # Read the model from the 'Meta' attribute. This even works in the admin,
            # as `modelform_factory()` includes a 'Meta' attribute.
            # The other options can be read from the base classes.
            form_new_meta = attrs.get('Meta', form_meta)
            form_model = form_new_meta.model if form_new_meta else form_meta.model

            # Detect all placeholders at this class level.
            placeholder_fields = [
                f_name for f_name, attr_value in six.iteritems(attrs) if isinstance(attr_value, TranslatedField)
            ]

            # Include the translated fields as attributes, pretend that these exist on the form.
            # This also works when assigning `form = TranslatableModelForm` in the admin,
            # since the admin always uses modelform_factory() on the form class, and therefore triggering this metaclass.
            if form_model:
                for translations_model in form_model._parler_meta.get_all_models():
                    fields = getattr(form_new_meta, 'fields', form_meta.fields)
                    exclude = getattr(form_new_meta, 'exclude', form_meta.exclude) or ()
                    widgets = getattr(form_new_meta, 'widgets', form_meta.widgets) or ()
                    formfield_callback = attrs.get('formfield_callback', None)

                    if fields == '__all__':
                        fields = None

                    for f_name in translations_model.get_translated_fields():
                        # Add translated field if not already added, and respect exclude options.
                        if f_name in placeholder_fields:
                            # The TranslatedField placeholder can be replaced directly with actual field, so do that.
                            attrs[f_name] = _get_model_form_field(translations_model, f_name, formfield_callback=formfield_callback, **attrs[f_name].kwargs)

                        # The next code holds the same logic as fields_for_model()
                        # The f.editable check happens in _get_model_form_field()
                        elif f_name not in form_base_fields \
                         and (fields is None or f_name in fields) \
                         and f_name not in exclude \
                         and not f_name in attrs:
                            # Get declared widget kwargs
                            if f_name in widgets:
                                # Not combined with declared fields (e.g. the TranslatedField placeholder)
                                kwargs = {'widget': widgets[f_name]}
                            else:
                                kwargs = {}

                            # See if this formfield was previously defined using a TranslatedField placeholder.
                            placeholder = _get_mro_attribute(bases, f_name)
                            if placeholder and isinstance(placeholder, TranslatedField):
                                kwargs.update(placeholder.kwargs)

                            # Add the form field as attribute to the class.
                            formfield = _get_model_form_field(translations_model, f_name, formfield_callback=formfield_callback, **kwargs)
                            if formfield is not None:
                                attrs[f_name] = formfield

        # Call the super class with updated `attrs` dict.
        return super(TranslatableModelFormMetaclass, mcs).__new__(mcs, name, bases, attrs)


def _get_mro_attribute(bases, name, default=None):
    for base in bases:
        try:
            return getattr(base, name)
        except AttributeError:
            continue
    return default


def _get_model_form_field(model, name, formfield_callback=None, **kwargs):
    """
    Utility to create the formfield from a model field.
    When a field is not editable, a ``None`` will be returned.
    """
    field = model._meta.get_field(name)
    if not field.editable:  # see fields_for_model() logic in Django.
        return None

    # Apply admin formfield_overrides
    if formfield_callback is None:
        formfield = field.formfield(**kwargs)
    elif not callable(formfield_callback):
        raise TypeError('formfield_callback must be a function or callable')
    else:
        formfield = formfield_callback(field, **kwargs)

    return formfield


if django.VERSION < (1, 5):
    # Django 1.4 doesn't recognize the use of with_metaclass.
    # This breaks the form initialization in modelform_factory()
    class TranslatableModelForm(BaseTranslatableModelForm, forms.ModelForm):
        __metaclass__ = TranslatableModelFormMetaclass
else:
    class TranslatableModelForm(compat.with_metaclass(TranslatableModelFormMetaclass, BaseTranslatableModelForm, forms.ModelForm)):
        """
        The model form to use for translated models.
        """

    # six.with_metaclass does not handle more than 2 parent classes for django < 1.6
    # but we need all of them in django 1.7 to pass check admin.E016:
    #       "The value of 'form' must inherit from 'BaseModelForm'"
    # so we use our copied version in parler.utils.compat
    #
    # Also, the class must inherit from ModelForm,
    # or the ModelFormMetaclass will skip initialization.
    # It only adds the _meta from anything that extends ModelForm.


class TranslatableBaseInlineFormSet(BaseInlineFormSet):
    """
    The formset base for creating inlines with translatable models.
    """
    language_code = None

    def _construct_form(self, i, **kwargs):
        form = super(TranslatableBaseInlineFormSet, self)._construct_form(i, **kwargs)
        form.language_code = self.language_code   # Pass the language code for new objects!
        return form

    def save_new(self, form, commit=True):
        obj = super(TranslatableBaseInlineFormSet, self).save_new(form, commit)
        return obj


# Backwards compatibility
TranslatableModelFormMixin = BaseTranslatableModelForm
