"""
Tests for counting.py, the comparison counter behind the "counted comparisons"
numbers in REPORT.md. If the counter were wrong, those numbers would be wrong.

Run from this folder:  python -m unittest -v
"""

import unittest

from counting import CountingKey, get_count, reset_count


class CountingKeyTests(unittest.TestCase):
    def setUp(self):
        reset_count()

    def test_every_comparison_operator_adds_exactly_one(self):
        a, b = CountingKey(1), CountingKey(2)
        for operator in ("lt", "le", "gt", "ge"):
            before = get_count()
            getattr(a, f"__{operator}__")(b)
            self.assertEqual(get_count(), before + 1, operator)

    def test_comparisons_give_the_same_answers_as_the_plain_values(self):
        pairs = [(1, 2), (2, 1), (3, 3)]
        for x, y in pairs:
            a, b = CountingKey(x), CountingKey(y)
            self.assertEqual(a < b, x < y)
            self.assertEqual(a <= b, x <= y)
            self.assertEqual(a > b, x > y)
            self.assertEqual(a >= b, x >= y)

    def test_reset_sets_the_count_back_to_zero(self):
        CountingKey(1) < CountingKey(2)
        self.assertGreater(get_count(), 0)
        reset_count()
        self.assertEqual(get_count(), 0)

    def test_sorting_with_builtin_sorted_counts_at_least_n_minus_one_comparisons(self):
        keys = [CountingKey(v) for v in (5, 1, 4, 2, 3)]
        sorted(keys)
        self.assertGreaterEqual(get_count(), len(keys) - 1)

    def test_value_is_kept(self):
        self.assertEqual(CountingKey(42).value, 42)


if __name__ == "__main__":
    unittest.main()
