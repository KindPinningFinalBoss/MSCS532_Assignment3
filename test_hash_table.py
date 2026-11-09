"""
Tests for hash_table.py.

Run from this folder:  python -m unittest -v
"""

import random
import unittest

from hash_table import PRIME, HashTable, UniversalHash


class BasicOperationTests(unittest.TestCase):
    def test_insert_then_search_returns_the_value(self):
        table = HashTable(rng=random.Random(1))
        table.insert("apple", 3)
        table.insert("pear", 5)
        self.assertEqual(table.search("apple"), 3)
        self.assertEqual(table.search("pear"), 5)
        self.assertEqual(len(table), 2)

    def test_search_for_missing_key_returns_default(self):
        table = HashTable(rng=random.Random(1))
        self.assertIsNone(table.search("nope"))
        self.assertEqual(table.search("nope", default=-1), -1)

    def test_default_is_not_confused_with_a_stored_none(self):
        table = HashTable(rng=random.Random(1))
        table.insert("k", None)
        self.assertEqual(table.search("k", default="missing"), None)
        self.assertIn("k", table)

    def test_inserting_an_existing_key_replaces_the_value(self):
        table = HashTable(rng=random.Random(1))
        table.insert("k", 1)
        table.insert("k", 2)
        self.assertEqual(table.search("k"), 2)
        self.assertEqual(len(table), 1)

    def test_delete_removes_the_key_and_reports_whether_it_existed(self):
        table = HashTable(rng=random.Random(1))
        table.insert("a", 1)
        table.insert("b", 2)
        self.assertTrue(table.delete("a"))
        self.assertIsNone(table.search("a"))
        self.assertEqual(table.search("b"), 2)
        self.assertEqual(len(table), 1)
        self.assertFalse(table.delete("a"))
        self.assertFalse(table.delete("never-there"))
        self.assertEqual(len(table), 1)

    def test_dict_style_helpers(self):
        table = HashTable(rng=random.Random(1))
        table["x"] = 10
        self.assertEqual(table["x"], 10)
        self.assertIn("x", table)
        self.assertNotIn("y", table)
        with self.assertRaises(KeyError):
            table["y"]
        del table["x"]
        self.assertNotIn("x", table)
        with self.assertRaises(KeyError):
            del table["x"]

    def test_mixed_key_types(self):
        table = HashTable(rng=random.Random(1))
        keys = [0, -1, 12345678901234567890, "text", (1, 2), 3.5, None, True]
        # True == 1, so skip it for the distinct-key check below.
        keys = [k for k in keys if k is not True]
        for i, key in enumerate(keys):
            table.insert(key, i)
        for i, key in enumerate(keys):
            self.assertEqual(table.search(key), i)

    def test_empty_table(self):
        table = HashTable(rng=random.Random(1))
        self.assertEqual(len(table), 0)
        self.assertEqual(table.load_factor, 0)
        self.assertFalse(table.delete(1))
        self.assertIsNone(table.search(1))


class ScaleTests(unittest.TestCase):
    def test_many_random_inserts_searches_and_deletes_match_a_dict(self):
        gen = random.Random(7)
        table = HashTable(rng=random.Random(8))
        reference = {}
        for _ in range(20_000):
            key = gen.randrange(5_000)
            action = gen.random()
            if action < 0.5:
                table.insert(key, key * 2)
                reference[key] = key * 2
            elif action < 0.75:
                self.assertEqual(table.search(key), reference.get(key))
            else:
                self.assertEqual(table.delete(key), key in reference)
                reference.pop(key, None)
            self.assertEqual(len(table), len(reference))
        for key, value in reference.items():
            self.assertEqual(table.search(key), value)

    def test_works_without_resizing_just_slower(self):
        table = HashTable(initial_capacity=8, resize=False, rng=random.Random(2))
        for k in range(500):
            table.insert(k, k)
        self.assertEqual(table.capacity, 8)  # never grew
        self.assertEqual(table.resize_count, 0)
        for k in range(500):
            self.assertEqual(table.search(k), k)
        self.assertGreater(table.load_factor, 60)


class ResizingTests(unittest.TestCase):
    def test_table_grows_so_load_factor_never_exceeds_the_limit(self):
        table = HashTable(initial_capacity=4, max_load_factor=1.0, rng=random.Random(3))
        for k in range(1000):
            table.insert(k, k)
            self.assertLessEqual(table.load_factor, 1.0)
        self.assertGreater(table.capacity, 4)
        self.assertGreater(table.resize_count, 0)

    def test_capacity_is_always_a_power_of_two_times_the_initial(self):
        table = HashTable(initial_capacity=4, rng=random.Random(3))
        for k in range(300):
            table.insert(k, k)
            ratio = table.capacity // 4
            self.assertEqual(table.capacity % 4, 0)
            self.assertEqual(ratio & (ratio - 1), 0)

    def test_contents_survive_every_resize(self):
        table = HashTable(initial_capacity=2, rng=random.Random(4))
        for k in range(600):
            table.insert(f"key{k}", k)
        for k in range(600):
            self.assertEqual(table.search(f"key{k}"), k)

    def test_table_shrinks_after_many_deletes_but_not_below_initial_capacity(self):
        table = HashTable(initial_capacity=8, rng=random.Random(5))
        for k in range(2000):
            table.insert(k, k)
        big = table.capacity
        for k in range(1990):
            table.delete(k)
        self.assertLess(table.capacity, big)
        self.assertGreaterEqual(table.capacity, 8)
        for k in range(1990, 2000):
            self.assertEqual(table.search(k), k)
        for k in range(1990, 2000):
            table.delete(k)
        self.assertEqual(len(table), 0)
        self.assertEqual(table.capacity, 8)

    def test_resizing_does_total_linear_rehash_work(self):
        # Doubling means the elements moved over all resizes add up to less
        # than 2n, which is why one insert costs O(1) amortized.
        table = HashTable(initial_capacity=4, max_load_factor=1.0, rng=random.Random(6))
        n = 10_000
        for k in range(n):
            table.insert(k, k)
        self.assertLess(table.rehash_moves, 2 * n)


class UniversalHashTests(unittest.TestCase):
    def test_hash_values_land_inside_the_table(self):
        gen = random.Random(11)
        for m in (1, 2, 7, 16, 1000):
            h = UniversalHash(m, rng=gen)
            for key in ("a", 17, -4, (1, 2), 10**30):
                self.assertGreaterEqual(h(key), 0)
                self.assertLess(h(key), m)

    def test_parameters_are_in_the_allowed_range(self):
        gen = random.Random(12)
        for _ in range(500):
            h = UniversalHash(64, rng=gen)
            self.assertTrue(1 <= h.a <= PRIME - 1)
            self.assertTrue(0 <= h.b <= PRIME - 1)

    def test_same_function_gives_same_answer(self):
        h = UniversalHash(32, rng=random.Random(13))
        self.assertEqual(h("hello"), h("hello"))

    def test_collision_probability_for_two_fixed_keys_is_at_most_about_one_over_m(self):
        # Universal means: over the random choice of h, two distinct keys
        # collide with probability at most 1/m.
        m, trials = 16, 20_000
        gen = random.Random(14)
        collisions = 0
        for _ in range(trials):
            h = UniversalHash(m, rng=gen)
            if h(123456) == h(654321):
                collisions += 1
        self.assertLess(collisions / trials, 1.25 / m)

    def test_keys_that_would_all_collide_under_k_mod_m_get_spread_out(self):
        m = 1024
        keys = [m * i for i in range(1000)]  # every one is 0 mod m
        table = HashTable(initial_capacity=m, max_load_factor=2.0, rng=random.Random(15))
        for key in keys:
            table.insert(key, key)
        # Under k mod m the longest chain would be 1000. Spread out, it is tiny.
        self.assertLess(table.max_chain_length(), 15)


class StatsTests(unittest.TestCase):
    def test_comparison_counter_counts_chain_steps(self):
        table = HashTable(initial_capacity=1, max_load_factor=100.0, resize=False,
                          rng=random.Random(16))
        for k in range(5):
            table.insert(k, k)  # one chain of length 5
        table.comparisons = 0
        table.search(999)  # unsuccessful search walks the whole chain
        self.assertEqual(table.comparisons, 5)

    def test_chain_lengths_add_up_to_the_number_of_items(self):
        table = HashTable(initial_capacity=16, rng=random.Random(17))
        for k in range(10):
            table.insert(k, k)
        lengths = table.chain_lengths()
        self.assertEqual(len(lengths), table.capacity)
        self.assertEqual(sum(lengths), len(table))
        self.assertEqual(table.max_chain_length(), max(lengths))


class ConstructorValidationTests(unittest.TestCase):
    def test_min_load_factor_must_be_at_most_a_quarter_of_max(self):
        # If min is close to max, one insert can trigger a grow and the next
        # delete a shrink, so nearly every operation would rebuild the table.
        with self.assertRaises(ValueError):
            HashTable(max_load_factor=1.0, min_load_factor=0.9)
        with self.assertRaises(ValueError):
            HashTable(max_load_factor=1.0, min_load_factor=0.26)
        HashTable(max_load_factor=1.0, min_load_factor=0.25)  # exactly a quarter is fine
        HashTable(max_load_factor=1.0, min_load_factor=0)

    def test_default_min_load_factor_is_a_quarter_of_max(self):
        self.assertEqual(HashTable().min_load_factor, 0.25)
        self.assertEqual(HashTable(max_load_factor=2.0).min_load_factor, 0.5)
        self.assertEqual(HashTable(max_load_factor=0.5).min_load_factor, 0.125)

    def test_other_bad_arguments_are_rejected(self):
        for kwargs in ({"initial_capacity": 0}, {"max_load_factor": 0}, {"max_load_factor": -1.0},
                       {"min_load_factor": -0.1}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    HashTable(**kwargs)


class RebuildCostTests(unittest.TestCase):
    def test_rehash_moves_counts_every_item_moved_by_every_rebuild(self):
        table = HashTable(initial_capacity=4, max_load_factor=1.0, rng=random.Random(1))
        for k in range(9):
            table.insert(k, k)
        # 4 -> 8 slots when the 5th item arrives (5 items move), then
        # 8 -> 16 slots when the 9th item arrives (9 items move).
        self.assertEqual(table.capacity, 16)
        self.assertEqual(table.resize_count, 2)
        self.assertEqual(table.rehash_moves, 5 + 9)

    def test_every_rebuild_draws_a_fresh_hash_function_from_the_tables_rng(self):
        class CountingRng:
            def __init__(self):
                self.calls = 0

            def randrange(self, lo, hi):
                self.calls += 1
                return lo + self.calls  # always inside the range

        rng = CountingRng()
        table = HashTable(initial_capacity=2, rng=rng)
        self.assertEqual(rng.calls, 2)  # a and b of the first function
        for k in range(3):
            table.insert(k, k)  # the third item grows the table from 2 to 4 slots
        self.assertEqual(table.resize_count, 1)
        self.assertEqual(rng.calls, 4)  # a and b were drawn again for the rebuild

    def test_a_table_already_at_its_minimum_size_does_not_rebuild_when_it_empties(self):
        table = HashTable(initial_capacity=8, rng=random.Random(2))
        for k in range(40):
            table.insert(k, k)
        for k in range(40):
            table.delete(k)
        self.assertEqual(table.capacity, 8)
        rebuilds = table.resize_count
        for k in range(5):
            table.insert(k, k)
        for k in range(5):
            table.delete(k)
        self.assertEqual(table.resize_count, rebuilds)

    def test_rebuild_work_stays_linear_in_the_number_of_operations(self):
        # Random mix of inserts and deletes.
        gen = random.Random(21)
        table = HashTable(initial_capacity=4, rng=random.Random(22))
        keys, ops = [], 30_000
        for _ in range(ops):
            if keys and gen.random() < 0.45:
                table.delete(keys.pop(gen.randrange(len(keys))))
            else:
                k = gen.getrandbits(40)
                keys.append(k)
                table.insert(k, k)
        self.assertLess(table.rehash_moves, 4 * ops)

    def test_sawtooth_workload_crossing_the_resize_limits_repeatedly_stays_linear(self):
        table = HashTable(initial_capacity=4, rng=random.Random(23))
        ops = 0
        for cycle in range(10):
            keys = [cycle * 10_000 + i for i in range(1000)]
            for k in keys:
                table.insert(k, k)
            for k in keys:
                table.delete(k)
            ops += 2000
        self.assertLess(table.rehash_moves, 4 * ops)


class PythonHashLimitTests(unittest.TestCase):
    def test_keys_whose_python_hashes_are_equal_collide_for_every_function(self):
        # hash() is applied before the universal function, so no choice of a
        # and b can separate two keys that already hash the same. In CPython
        # hash(-1) == hash(-2) == -2. REPORT.md and the module docstring say so.
        self.assertEqual(hash(-1), hash(-2))
        gen = random.Random(5)
        for _ in range(200):
            h = UniversalHash(64, rng=gen)
            self.assertEqual(h(-1), h(-2))


if __name__ == "__main__":
    unittest.main()
