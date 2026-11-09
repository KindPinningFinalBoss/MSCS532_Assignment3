"""
Tests for randomized_quicksort.py.

Run from this folder:  python -m unittest -v
"""

import random
import unittest

from counting import CountingKey, reset_count, get_count
from randomized_quicksort import deterministic_quicksort, randomized_quicksort

# Every sorter gets run through the same tests. The lambdas fix the seed so a
# failure can be reproduced.
SORTERS = {
    "randomized/three_way": lambda a: randomized_quicksort(a, rng=random.Random(1)),
    "randomized/lomuto": lambda a: randomized_quicksort(
        a, rng=random.Random(1), partition="lomuto"
    ),
    "deterministic/three_way": lambda a: deterministic_quicksort(a),
    "deterministic/lomuto": lambda a: deterministic_quicksort(a, partition="lomuto"),
}

EDGE_CASES = {
    "empty": [],
    "single": [7],
    "two sorted": [1, 2],
    "two reversed": [2, 1],
    "two equal": [3, 3],
    "already sorted": list(range(50)),
    "reverse sorted": list(range(50, 0, -1)),
    "all equal": [5] * 40,
    "few distinct values": [(i * 7) % 3 for i in range(200)],
    "negatives and zeros": [-5, 0, 3, -2, 0, 9, -5],
    "floats": [3.5, -1.25, 2.0, 2.0, 0.0],
    "strings": ["pear", "apple", "fig", "apple", "kiwi"],
}


class RecordingRng:
    """Stands in for random.Random and remembers every randint call."""

    def __init__(self, pick):
        self.calls = []
        self._pick = pick  # function (lo, hi) -> index to return

    def randint(self, lo, hi):
        self.calls.append((lo, hi))
        return self._pick(lo, hi)


class CorrectnessTests(unittest.TestCase):
    def test_edge_cases_match_builtin_sorted(self):
        for sorter_name, sorter in SORTERS.items():
            for case_name, data in EDGE_CASES.items():
                with self.subTest(sorter=sorter_name, case=case_name):
                    arr = list(data)
                    sorter(arr)
                    self.assertEqual(arr, sorted(data))

    def test_sorts_in_place_and_returns_same_list(self):
        for sorter_name, sorter in SORTERS.items():
            with self.subTest(sorter=sorter_name):
                arr = [3, 1, 2]
                result = sorter(arr)
                self.assertIs(result, arr)
                self.assertEqual(arr, [1, 2, 3])

    def test_random_arrays_match_builtin_sorted(self):
        gen = random.Random(2024)
        for sorter_name, sorter in SORTERS.items():
            for trial in range(150):
                n = gen.randint(0, 60)
                data = [gen.randint(-20, 20) for _ in range(n)]
                with self.subTest(sorter=sorter_name, trial=trial):
                    arr = list(data)
                    sorter(arr)
                    self.assertEqual(arr, sorted(data))

    def test_unknown_partition_scheme_is_rejected(self):
        with self.assertRaises(ValueError):
            randomized_quicksort([3, 1, 2], partition="hoare-ish")
        with self.assertRaises(ValueError):
            deterministic_quicksort([3, 1, 2], partition="nope")


class PivotChoiceTests(unittest.TestCase):
    def test_randomized_asks_rng_for_an_index_inside_the_subarray(self):
        rng = RecordingRng(lambda lo, hi: hi)  # always take the last element
        arr = [9, 4, 7, 1, 8, 2, 6]
        randomized_quicksort(arr, rng=rng, partition="lomuto")
        self.assertEqual(arr, sorted(arr))
        self.assertGreater(len(rng.calls), 0)
        self.assertEqual(rng.calls[0], (0, len(arr) - 1))  # first call spans everything
        for lo, hi in rng.calls:
            self.assertLessEqual(lo, hi)
            self.assertGreaterEqual(lo, 0)
            self.assertLess(hi, len(arr))

    def test_randomized_is_correct_for_any_pivot_choice(self):
        data = [5, 3, 9, 3, 1, 8, 8, 2, 7, 0]
        picks = {
            "first": lambda lo, hi: lo,
            "last": lambda lo, hi: hi,
            "middle": lambda lo, hi: (lo + hi) // 2,
        }
        for scheme in ("lomuto", "three_way"):
            for name, pick in picks.items():
                with self.subTest(scheme=scheme, pivot=name):
                    arr = list(data)
                    randomized_quicksort(arr, rng=RecordingRng(pick), partition=scheme)
                    self.assertEqual(arr, sorted(data))

    def test_pivot_requests_do_not_depend_on_the_global_random_state(self):
        # All randomness has to come from the rng that was passed in. Two runs
        # with the same stand-in rng must ask for the same (lo, hi) ranges even
        # when the global random generator is in a different state.
        data = list(range(200))
        random.Random(5).shuffle(data)
        pick = lambda lo, hi: random.Random(lo * 1000 + hi).randint(lo, hi)
        first, second = RecordingRng(pick), RecordingRng(pick)
        random.seed(1)
        randomized_quicksort(list(data), rng=first)
        random.seed(2)
        randomized_quicksort(list(data), rng=second)
        self.assertGreater(len(first.calls), 0)
        self.assertEqual(first.calls, second.calls)


class ComparisonCountTests(unittest.TestCase):
    """Counts comparisons by wrapping the keys. See counting.py."""

    @staticmethod
    def _count(sorter, values):
        reset_count()
        arr = [CountingKey(v) for v in values]
        sorter(arr)
        assert [k.value for k in arr] == sorted(values)
        return get_count()

    def test_deterministic_lomuto_on_sorted_input_is_exactly_quadratic(self):
        # First-element pivot on sorted data peels off one element per pass,
        # so the partitions cost (n-1) + (n-2) + ... + 1 = n(n-1)/2 comparisons.
        n = 100
        sorter = SORTERS["deterministic/lomuto"]
        self.assertEqual(self._count(sorter, list(range(n))), n * (n - 1) // 2)
        self.assertEqual(self._count(sorter, list(range(n, 0, -1))), n * (n - 1) // 2)

    def test_deterministic_pivot_is_the_first_element(self):
        # [2, 1, 3] with first-element pivot 2 splits evenly: 2 comparisons.
        # A last-element pivot (3) would need 3, so the count tells them apart.
        sorter = SORTERS["deterministic/lomuto"]
        self.assertEqual(self._count(sorter, [2, 1, 3]), 2)

    def test_randomized_lomuto_on_sorted_input_is_nowhere_near_quadratic(self):
        n = 1000
        count = self._count(SORTERS["randomized/lomuto"], list(range(n)))
        self.assertLess(count, 30_000)  # quadratic would be 499,500
        self.assertGreater(count, 5_000)

    def test_randomized_lomuto_matches_expected_comparisons_on_random_input(self):
        # With distinct keys the expected number of comparisons is
        # 2(n+1)H_n - 4n, where H_n is the n-th harmonic number.
        n, trials = 500, 40
        gen = random.Random(99)
        total = 0
        for t in range(trials):
            values = list(range(n))
            gen.shuffle(values)
            total += self._count(
                lambda a, t=t: randomized_quicksort(
                    a, rng=random.Random(1000 + t), partition="lomuto"
                ),
                values,
            )
        mean = total / trials
        harmonic = sum(1 / k for k in range(1, n + 1))
        expected = 2 * (n + 1) * harmonic - 4 * n
        self.assertAlmostEqual(mean / expected, 1.0, delta=0.05)

    def test_three_way_handles_all_equal_input_in_linear_comparisons(self):
        n = 10_000
        count = self._count(SORTERS["randomized/three_way"], [4] * n)
        self.assertLessEqual(count, 2 * n + 10)

    def test_three_way_handles_few_distinct_values_in_n_log_k_comparisons(self):
        n, k = 20_000, 5
        gen = random.Random(3)
        values = [gen.randrange(k) for _ in range(n)]
        count = self._count(SORTERS["randomized/three_way"], values)
        # Each level of recursion splits off a whole group of equal keys, so
        # there are at most about k levels. Generous bound: 2 * n * (k + 2).
        self.assertLess(count, 2 * n * (k + 2))


class RecursionDepthTests(unittest.TestCase):
    def test_worst_case_input_does_not_hit_python_recursion_limit(self):
        # Plain recursion on a sorted array with a first-element pivot would be
        # about n levels deep. Recursing into the smaller side first caps the
        # depth at about log2(n) even when the partitions are lopsided.
        n = 3000  # well past Python's default limit of 1000
        for sorter_name in ("deterministic/lomuto", "deterministic/three_way"):
            with self.subTest(sorter=sorter_name):
                arr = list(range(n))
                SORTERS[sorter_name](arr)
                self.assertEqual(arr, list(range(n)))

    def test_all_equal_with_lomuto_does_not_hit_recursion_limit(self):
        arr = [1] * 2000
        SORTERS["randomized/lomuto"](arr)
        self.assertEqual(arr, [1] * 2000)


if __name__ == "__main__":
    unittest.main()
