# MSCS532_Assignment3

Randomized Quicksort and a hash table with chaining, written in Python, with the analysis and experiments for Assignment 3 of MSCS-532 (Algorithms and Data Structures): *Understanding Algorithm Efficiency and Scalability*.

**The written report is [`REPORT.md`](REPORT.md).** It has the theoretical analysis, the empirical comparisons, and a discussion of where the results do and do not match the theory.

## What is in here

| File | What it is |
|---|---|
| `randomized_quicksort.py` | `randomized_quicksort` (uniformly random pivot) and `deterministic_quicksort` (first element as pivot). Both sort in place. Two partition schemes: `"three_way"` (default, fast on repeated values) and `"lomuto"` (the textbook one). |
| `hash_table.py` | `HashTable`: chaining, a random hash function from a universal family, `insert` / `search` / `delete`, and dynamic resizing. |
| `counting.py` | A tiny helper that counts comparisons, used by the tests and benchmarks. |
| `test_quicksort.py`, `test_hash_table.py`, `test_counting.py` | 51 unit tests. |
| `mutation_check.py` | Breaks the code on purpose in 18 ways and checks that the tests fail (output in `results/mutation_check.txt`). |
| `benchmark_quicksort.py` | Experiments for Part 1 (timings and comparison counts). |
| `benchmark_hashing.py` | Experiments for Part 2. |
| `check_structured_keys.py` | A small side check described in section 2.3 of the report. |
| `make_plots.py` | Draws the charts in `figures/` from the CSV files in `results/`. |
| `results/` | The raw numbers behind every table in the report (CSV), plus `environment.txt`. |
| `figures/` | The charts used in the report. |

## How to run it

The sorting and hashing code uses only the Python standard library (Python 3.10 or newer; written and tested on 3.13). Nothing to install.

Try the sorts on a few sample arrays:

```
python randomized_quicksort.py
```

Run the tests (about one second):

```
python -m unittest -v
```

Rerun the experiments (a few minutes each; the numbers will differ a little on another machine):

```
python benchmark_quicksort.py
python benchmark_hashing.py
python check_structured_keys.py
```

Add `--quick` to either benchmark for a small run that finishes in seconds (it writes to `results_quick/`, not `results/`), or `--only a` / `--only h1` and similar to run one experiment. `python mutation_check.py` reruns the deliberate-bug check. The charts need matplotlib (`pip install matplotlib`):

```
python make_plots.py
```

### Using the code

```python
import random
from randomized_quicksort import randomized_quicksort, deterministic_quicksort
from hash_table import HashTable

data = [5, 2, 9, 2, 7]
randomized_quicksort(data, rng=random.Random(1))   # sorts in place, returns the list
deterministic_quicksort(data, partition="lomuto")

table = HashTable()
table.insert("apple", 3)
table.search("apple")          # 3
table.search("pear", default=0)  # 0
table.delete("apple")          # True
```

## Summary of the findings

- **Randomized Quicksort is O(n log n) on average for every input order.** The expected number of comparisons for distinct keys is 2(n+1)Hₙ − 4n. Counted comparisons were within about 1% of it for n up to 4,000, on random input *and* on already-sorted input.
- **First-element Quicksort is quadratic on sorted and reverse-sorted input** (textbook partition: 1.58 s and 2.66 s at n = 8,000, against 0.017 s for the randomized version).
- **On random input the deterministic version is faster** (32% at n = 1,000, 15% at n = 8,000; pivot luck only moves a run by about 4 to 7%). My explanation, which I did not profile, is that the randomized one pays for picking a random number at every partition.
- **Repeated values need a three-way partition.** With 10 distinct values the textbook partition was quadratic for *both* versions (0.38 s at n = 8,000); the three-way partition took 0.003 s.
- **Hash table with chaining:** measured comparisons per search matched 1 + α/2 (hit) and α (miss), where α = n/m is the load factor. With resizing, time per operation stayed almost flat from 1,000 to 128,000 items; a fixed 1,024-slot table was about 12 times slower at 128,000 items.
- **Universal hashing is a promise about the average over random choices, not about every table.** For keys that are all multiples of the table size, the average matched theory but about 1 table in 30 was more than twice as slow as the bound.

## Environment used for the timings

AMD Ryzen 7 3700X, Windows 11, Python 3.13.9. See `results/environment.txt`.

## References

Carter, J. L., & Wegman, M. N. (1979). Universal classes of hash functions. *Journal of Computer and System Sciences, 18*(2), 143–154. https://doi.org/10.1016/0022-0000(79)90044-8

Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). *Introduction to algorithms* (4th ed.). MIT Press.

Hoare, C. A. R. (1962). Quicksort. *The Computer Journal, 5*(1), 10–16. https://doi.org/10.1093/comjnl/5.1.10
