"""
Coverage gap tests for parler/forms.py.
Targets lines: 68-71, 103, 106, 121, 166-167, 173-174, 209-215, 230, 289, 307, 355, 360-363, 397-398
"""
from unittest.mock import MagicMock, patch

from django import forms
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import BoundField, inlineformset_factory

from parler.forms import (
    TranslatableBaseInlineFormSet,
    TranslatableBoundField,
    TranslatableModelForm,
    TranslatedField,
    _get_model_form_field,
)

from .testapp.models import (
    ForeignKeyTranslationModel,
    IntegerPrimaryKeyModel,
    IntegerPrimaryKeyRelatedModel,
    RegularModel,
    SimpleModel,
)
from .utils import AppTestCase


class SimpleForm(TranslatableModelForm):
    class Meta:
        model = SimpleModel
        fields = "__all__"


class ForeignKeyTranslationModelForm(TranslatableModelForm):
    class Meta:
        model = ForeignKeyTranslationModel
        fields = "__all__"


# ---------------------------------------------------------------------------
# Lines 68-71: except ObjectDoesNotExist in __init__ when loading initial values
# ---------------------------------------------------------------------------


class InitObjectDoesNotExistTests(AppTestCase):
    def test_value_from_object_exception_is_silenced(self):
        """ObjectDoesNotExist from value_from_object is silently ignored (lines 68-71)."""
        r1 = RegularModel.objects.create(original_field="r1")
        instance = ForeignKeyTranslationModel.objects.create(
            translated_foreign=r1, shared="EN"
        )
        translation_model = instance._parler_meta[0].model
        fk_field = translation_model._meta.get_field("translated_foreign")
        with patch.object(
            fk_field, "value_from_object", side_effect=ObjectDoesNotExist("gone")
        ):
            form = ForeignKeyTranslationModelForm(instance=instance)
        self.assertIsNotNone(form)


# ---------------------------------------------------------------------------
# Lines 103, 106, 121: _get_translation_validation_exclusions branches
# ---------------------------------------------------------------------------


class ValidationExclusionsBranchTests(AppTestCase):
    def _make_valid_form(self):
        form = SimpleForm(data={"shared": "test", "tr_title": "test"})
        form.language_code = "en"
        form.is_valid()
        return form

    def test_field_in_form_but_not_in_meta_fields_is_excluded(self):
        """tr_title in form.fields but not in _meta.fields → excluded (line 103)."""
        form = self._make_valid_form()
        translation = form.instance._get_translated_model()
        form._meta.fields = ("shared",)  # real tuple, tr_title not in it
        result = form._get_translation_validation_exclusions(translation)
        self.assertIn("tr_title", result)

    def test_field_in_meta_exclude_is_excluded(self):
        """tr_title in _meta.exclude → excluded (line 106)."""
        form = self._make_valid_form()
        translation = form.instance._get_translated_model()
        form._meta.fields = None
        form._meta.exclude = ("tr_title",)
        result = form._get_translation_validation_exclusions(translation)
        self.assertIn("tr_title", result)

    def test_blank_false_not_required_empty_triggers_exclusion(self):
        """blank=False model field + required=False form field + empty value → excluded (line 121)."""
        form = SimpleForm(data={"shared": "test", "tr_title": ""})
        form.language_code = "en"
        form.fields["tr_title"].required = False
        # is_valid() triggers full_clean → _post_clean → _get_translation_validation_exclusions
        result = form.is_valid()
        # Form succeeds because tr_title is excluded from model full_clean
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# Lines 166-167, 173-174: ValidationError handling in _post_clean_translation
# ---------------------------------------------------------------------------


class PostCleanTranslationErrorTests(AppTestCase):
    def test_full_clean_validation_error_is_collected(self):
        """ValidationError from translation.full_clean() is caught (lines 166-167)."""
        translation_model = SimpleModel._parler_meta[0].model
        form = SimpleForm(data={"shared": "test", "tr_title": "test"})
        form.language_code = "en"
        with patch.object(
            translation_model, "full_clean", side_effect=ValidationError("forced error")
        ):
            result = form.is_valid()
        self.assertFalse(result)

    def test_validate_unique_validation_error_is_collected(self):
        """ValidationError from translation.validate_unique() is caught (lines 173-174)."""
        translation_model = SimpleModel._parler_meta[0].model
        form = SimpleForm(data={"shared": "test", "tr_title": "test"})
        form.language_code = "en"
        # Use a dict-based ValidationError so that parler/models.py:748
        # (errors.update(e.error_dict)) also works when this mock is called
        # from TranslatableModel.validate_unique() during the form's validate_unique().
        with patch.object(
            translation_model,
            "validate_unique",
            side_effect=ValidationError({"__all__": ["uniq error"]}),
        ):
            result = form.is_valid()
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# Lines 209-215: _upgrade_boundfield_class creates combined subclass
# ---------------------------------------------------------------------------


class CustomBoundField(BoundField):
    pass


class CustomCharField(forms.CharField):
    def get_bound_field(self, form, field_name):
        return CustomBoundField(form, self, field_name)


class UpgradeBoundFieldCombinedTests(AppTestCase):
    def test_custom_bound_field_class_is_combined_with_translatable(self):
        """A non-BoundField, non-TranslatableBoundField subclass gets combined (lines 209-215)."""

        class CustomSimpleForm(TranslatableModelForm):
            tr_title = CustomCharField()

            class Meta:
                model = SimpleModel
                fields = "__all__"

        form = CustomSimpleForm(_current_language="en")
        bound = form["tr_title"]
        self.assertIsInstance(bound, TranslatableBoundField)
        self.assertIsInstance(bound, CustomBoundField)
        # Second access uses the cached combined class (also hits the try/return in UPGRADED_CLASSES)
        bound2 = form["tr_title"]
        self.assertIsInstance(bound2, TranslatableBoundField)


# ---------------------------------------------------------------------------
# Line 230: TranslatableBoundField.label_tag with attrs=None
# ---------------------------------------------------------------------------


class TranslatableBoundFieldLabelTagTests(AppTestCase):
    def test_label_tag_without_attrs_sets_empty_dict(self):
        """label_tag() with attrs=None sets attrs={} (line 230)."""
        form = SimpleForm(_current_language="en")
        bound = form["tr_title"]
        self.assertIsInstance(bound, TranslatableBoundField)
        result = bound.label_tag()
        self.assertIn("translatable-field", result)


# ---------------------------------------------------------------------------
# Lines 289, 307: Metaclass formfield_callback and widgets branches
# ---------------------------------------------------------------------------


class MetaclassFormfieldCallbackTests(AppTestCase):
    def test_formfield_callback_is_called_for_translated_fields(self):
        """formfield_callback in class attrs is used for translated fields (line 289).

        Line 289 is reached only when a translated field is declared as a
        TranslatedField() placeholder IN the form class AND a formfield_callback
        is also present.  The metaclass then replaces the placeholder using
        _get_model_form_field(..., formfield_callback=...).
        """
        callback_calls = []

        def my_callback(field, **kwargs):
            callback_calls.append(field.name)
            return field.formfield(**kwargs)

        # tr_title = TranslatedField() puts "tr_title" into placeholder_fields;
        # formfield_callback causes the metaclass to take the line-289 branch.
        CustomForm = type(
            "CustomForm",
            (TranslatableModelForm,),
            {
                "Meta": type("Meta", (), {"model": SimpleModel, "fields": "__all__"}),
                "formfield_callback": my_callback,
                "tr_title": TranslatedField(),
            },
        )
        self.assertIn("tr_title", callback_calls)

    def test_widgets_dict_used_for_translated_field(self):
        """widgets in Meta is applied to translated field formfield (line 307)."""

        class WidgetForm(TranslatableModelForm):
            class Meta:
                model = SimpleModel
                fields = "__all__"
                widgets = {"tr_title": forms.Textarea()}

        self.assertIsInstance(WidgetForm.base_fields["tr_title"].widget, forms.Textarea)


# ---------------------------------------------------------------------------
# Lines 355, 360-363: _get_model_form_field function branches
# ---------------------------------------------------------------------------


class GetModelFormFieldTests(AppTestCase):
    def test_non_editable_field_returns_none(self):
        """Returns None for non-editable field (line 355)."""
        translation_model = SimpleModel._parler_meta[0].model
        mock_field = MagicMock()
        mock_field.editable = False
        with patch.object(translation_model._meta, "get_field", return_value=mock_field):
            result = _get_model_form_field(translation_model, "tr_title")
        self.assertIsNone(result)

    def test_non_callable_formfield_callback_raises_type_error(self):
        """Raises TypeError when formfield_callback is not callable (lines 360-361)."""
        translation_model = SimpleModel._parler_meta[0].model
        with self.assertRaises(TypeError):
            _get_model_form_field(
                translation_model, "tr_title", formfield_callback="not_callable"
            )

    def test_callable_formfield_callback_is_invoked(self):
        """Callable formfield_callback is called with the field (lines 362-363)."""
        translation_model = SimpleModel._parler_meta[0].model
        called_with = []

        def my_callback(field, **kwargs):
            called_with.append(field.name)
            return field.formfield(**kwargs)

        result = _get_model_form_field(
            translation_model, "tr_title", formfield_callback=my_callback
        )
        self.assertIsNotNone(result)
        self.assertIn("tr_title", called_with)


# ---------------------------------------------------------------------------
# Lines 397-398: TranslatableBaseInlineFormSet.save_new
# ---------------------------------------------------------------------------


class TranslatableBaseInlineFormSetSaveNewTests(AppTestCase):
    def test_save_new_delegates_to_super(self):
        """save_new delegates to super and returns the new object (lines 397-398).

        IntegerPrimaryKeyRelatedModel has no editable fields beyond the FK, so
        an inline form is always "empty" from Django's perspective and formset.save()
        skips calling save_new.  Call save_new directly on a valid form instead.
        """
        InlineFormSet = inlineformset_factory(
            IntegerPrimaryKeyModel,
            IntegerPrimaryKeyRelatedModel,
            fields=(),
            formset=TranslatableBaseInlineFormSet,
        )
        parent = IntegerPrimaryKeyModel(_current_language="en")
        parent.tr_title = "test parent"
        parent.save()

        formset = InlineFormSet(
            instance=parent,
            data={
                "children-TOTAL_FORMS": 1,
                "children-INITIAL_FORMS": 0,
                "children-MIN_NUM_FORMS": 0,
                "children-MAX_NUM_FORMS": 1000,
            },
        )
        formset.language_code = "en"
        self.assertTrue(formset.is_valid())

        # Call save_new directly — the inline form is "empty" so formset.save()
        # would skip it, but save_new must still work when called directly.
        form = formset.forms[0]
        obj = formset.save_new(form, commit=False)
        self.assertIsNotNone(obj)
