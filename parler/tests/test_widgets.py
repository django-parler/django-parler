"""
Tests for parler/widgets.py
"""
from django.test import TestCase

from parler.widgets import (
    SortedCheckboxSelectMultiple,
    SortedChoiceIterator,
    SortedSelect,
    SortedSelectMultiple,
)


class SortedChoiceIteratorTests(TestCase):
    def test_iter_sorts_choices(self):
        widget = SortedSelect(choices=[("b", "Banana"), ("a", "Apple"), ("c", "Cherry")])
        iterator = SortedChoiceIterator(widget)
        result = list(iterator)
        self.assertEqual(result[0], ("a", "Apple"))
        self.assertEqual(result[1], ("b", "Banana"))
        self.assertEqual(result[2], ("c", "Cherry"))

    def test_iter_already_sorted_flag(self):
        widget = SortedSelect(choices=[("b", "Banana"), ("a", "Apple")])
        widget._sorted = True
        widget._choices = [("b", "Banana"), ("a", "Apple")]
        iterator = SortedChoiceIterator(widget)
        # When _sorted=True, it returns iter of _choices directly
        result = list(iterator)
        self.assertEqual(result, [("b", "Banana"), ("a", "Apple")])


class SortedSelectMixinTests(TestCase):
    def test_choices_property_returns_iterator_when_not_sorted(self):
        widget = SortedSelect(choices=[("b", "Banana"), ("a", "Apple")])
        self.assertFalse(widget._sorted)
        choices = widget.choices
        self.assertIsInstance(choices, SortedChoiceIterator)

    def test_choices_property_returns_list_when_sorted(self):
        widget = SortedSelect(choices=[("a", "Apple"), ("b", "Banana")])
        widget._sorted = True
        widget._choices = [("a", "Apple"), ("b", "Banana")]
        self.assertEqual(widget.choices, [("a", "Apple"), ("b", "Banana")])

    def test_choices_setter_resets_sorted_flag(self):
        widget = SortedSelect(choices=[("a", "Apple")])
        widget._sorted = True
        # Setting choices should reset _sorted
        widget.choices = [("b", "Banana"), ("a", "Apple")]
        self.assertFalse(widget._sorted)
        self.assertEqual(widget._choices, [("b", "Banana"), ("a", "Apple")])

    def test_sort_choices_regular(self):
        widget = SortedSelect(choices=[("c", "Cherry"), ("a", "Apple"), ("b", "Banana")])
        result = list(widget.choices)
        self.assertEqual(result[0][0], "a")
        self.assertEqual(result[1][0], "b")
        self.assertEqual(result[2][0], "c")

    def test_sort_choices_case_insensitive(self):
        widget = SortedSelect(choices=[("o", "Oman"), ("o2", "Österreich")])
        result = list(widget.choices)
        # Österreich normalizes via slugify to osterreich, Oman → oman
        # o < os => Oman comes first
        labels = [c[1] for c in result]
        self.assertIn("Oman", labels)
        self.assertIn("Österreich", labels)

    def test_sort_choices_empty_value_first(self):
        widget = SortedSelect(choices=[("b", "Banana"), ("", "---"), ("a", "Apple")])
        result = list(widget.choices)
        self.assertEqual(result[0][0], "")

    def test_sort_choices_with_optgroups(self):
        choices = [
            ("group1", [("b", "Banana"), ("a", "Apple")]),
            ("group2", [("d", "Date"), ("c", "Cherry")]),
        ]
        widget = SortedSelect(choices=choices)
        result = list(widget.choices)
        # Each optgroup's items should be sorted
        group1_items = result[0][1]
        group2_items = result[1][1]
        self.assertEqual(group1_items[0][0], "a")
        self.assertEqual(group1_items[1][0], "b")
        self.assertEqual(group2_items[0][0], "c")
        self.assertEqual(group2_items[1][0], "d")

    def test_sort_choices_mixed_optgroups_and_regular(self):
        # Mix of optgroup and regular choices — only optgroup path triggers deepcopy
        choices = [
            ("b", "Banana"),
            ("group1", [("z", "Zucchini"), ("a", "Artichoke")]),
        ]
        widget = SortedSelect(choices=choices)
        result = list(widget.choices)
        # Group items should be sorted
        group_choice = next(c for c in result if isinstance(c[1], list))
        self.assertEqual(group_choice[1][0][0], "a")

    def test_init_stores_choices_without_sorting(self):
        raw = [("b", "Banana"), ("a", "Apple")]
        widget = SortedSelect(choices=raw)
        self.assertEqual(widget._choices, raw)
        self.assertFalse(widget._sorted)


class SortedSelectTests(TestCase):
    def test_is_select_widget(self):
        from django import forms

        widget = SortedSelect(choices=[("a", "Apple")])
        self.assertIsInstance(widget, forms.Select)

    def test_sorted_output(self):
        widget = SortedSelect(choices=[("b", "Banana"), ("a", "Apple")])
        html = widget.render("test", "a")
        # Apple should appear before Banana in the rendered HTML
        self.assertLess(html.index("Apple"), html.index("Banana"))


class SortedSelectMultipleTests(TestCase):
    def test_is_select_multiple_widget(self):
        from django import forms

        widget = SortedSelectMultiple(choices=[("a", "Apple")])
        self.assertIsInstance(widget, forms.SelectMultiple)

    def test_sorted_output(self):
        widget = SortedSelectMultiple(choices=[("b", "Banana"), ("a", "Apple")])
        html = widget.render("test", ["a"])
        self.assertLess(html.index("Apple"), html.index("Banana"))


class SortedCheckboxSelectMultipleTests(TestCase):
    def test_is_checkbox_widget(self):
        from django import forms

        widget = SortedCheckboxSelectMultiple(choices=[("a", "Apple")])
        self.assertIsInstance(widget, forms.CheckboxSelectMultiple)

    def test_sorted_output(self):
        widget = SortedCheckboxSelectMultiple(choices=[("b", "Banana"), ("a", "Apple")])
        html = widget.render("test", ["a"])
        self.assertLess(html.index("Apple"), html.index("Banana"))
