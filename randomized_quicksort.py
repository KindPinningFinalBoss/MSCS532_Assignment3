"""
Randomized Quicksort and Deterministic Quicksort.

MSCS-532 Assignment 3, Part 1.

Both sorts work in place and share all their code except one line: how the
pivot is picked.

    randomized_quicksort     pivot index chosen uniformly at random from the
                             subarray being partitioned
    deterministic_quicksort  pivot is always the first element of the subarray

Two partition schemes are available for each:

    "three_way"  (default)  splits the subarray into  < pivot | == pivot | > pivot.
                            Elements equal to the pivot are done after one pass,
                            so arrays with many repeated values stay fast.
    "lomuto"                the textbook two-way partition (Cormen et al.,
                            Introduction to Algorithms). Kept so the benchmarks
                            can show what repeated values do to it.

Recursion only goes into the smaller side. The bigger side is handled by the
loop, so the stack never gets deeper than about log2(n) even when the
partitions are badly lopsided (a sorted array with a first-element pivot).
Without that, a sorted array of 3,000 numbers would blow past Python's default
recursion limit of 1,000.
"""

import random


def _lomuto_partition(a, lo, hi, pivot_index):
    """Two-way partition of a[lo..hi] around a[pivot_index].

    Returns (q, q) where q is the final position of the pivot. Everything left
    of q is <= the pivot and everything right of q is > the pivot.
    """
    a[pivot_index], a[hi] = a[hi], a[pivot_index]  # park the pivot at the end
    pivot = a[hi]
    i = lo - 1
    for j in range(lo, hi):
        if a[j] <= pivot:
            i += 1
            a[i], a[j] = a[j], a[i]
    a[i + 1], a[hi] = a[hi], a[i + 1]
    return i + 1, i + 1


def _three_way_partition(a, lo, hi, pivot_index):
    """Three-way partition of a[lo..hi] around a[pivot_index].

    Returns (lt, gt) so that a[lo..lt-1] < pivot, a[lt..gt] == pivot and
    a[gt+1..hi] > pivot. This is the "Dutch national flag" scan.
    """
    pivot = a[pivot_index]
    lt, i, gt = lo, lo, hi
    while i <= gt:
        x = a[i]
        if x < pivot:
            a[lt], a[i] = a[i], a[lt]
            lt += 1
            i += 1
        elif x > pivot:
            a[i], a[gt] = a[gt], a[i]
            gt -= 1
        else:
            i += 1
    return lt, gt


_PARTITIONS = {
    "three_way": _three_way_partition,
    "lomuto": _lomuto_partition,
}


def _get_partition(name):
    try:
        return _PARTITIONS[name]
    except KeyError:
        raise ValueError(
            f"unknown partition scheme {name!r}; use one of {sorted(_PARTITIONS)}"
        ) from None


def _quicksort(a, lo, hi, choose_pivot, partition):
    while lo < hi:
        p = choose_pivot(lo, hi)
        lt, gt = partition(a, lo, hi, p)
        # Recurse on the smaller side, loop on the larger side.
        if lt - lo < hi - gt:
            _quicksort(a, lo, lt - 1, choose_pivot, partition)
            lo = gt + 1
        else:
            _quicksort(a, gt + 1, hi, choose_pivot, partition)
            hi = lt - 1


def randomized_quicksort(arr, *, rng=None, partition="three_way"):
    """Sort a list in place with a uniformly random pivot at every step.

    rng       anything with a randint(lo, hi) method (inclusive on both ends),
              such as random.Random(seed). Defaults to the random module.
    partition "three_way" (default) or "lomuto".

    Returns the same list so it can also be used inline.
    """
    part = _get_partition(partition)
    pick = (rng if rng is not None else random).randint
    _quicksort(arr, 0, len(arr) - 1, pick, part)
    return arr


def deterministic_quicksort(arr, *, partition="three_way"):
    """Sort a list in place, always using the first element as the pivot.

    Same interface as randomized_quicksort. With the "lomuto" partition, both
    sorted and reverse-sorted input are quadratic. With the default "three_way"
    partition, reverse-sorted input is still quadratic, but sorted input grows
    more slowly (about n^1.5 in the measurements in REPORT.md), because the
    three-way scan swaps elements in from the far end and so reshuffles the
    array while it partitions.
    """
    part = _get_partition(partition)
    _quicksort(arr, 0, len(arr) - 1, lambda lo, hi: lo, part)
    return arr


def main():
    samples = [
        [5, 2, 4, 6, 1, 3],
        [],
        [42],
        [9, 9, 1, 9, 2],
        [1, 2, 3, 4, 5],
        [5, 4, 3, 2, 1],
        [-3, 7, 0, -8, 4],
        [7] * 6,
    ]
    for name, sorter in (
        ("randomized", lambda a: randomized_quicksort(a, rng=random.Random(0))),
        ("deterministic", deterministic_quicksort),
    ):
        print(f"--- {name} ---")
        for data in samples:
            original = list(data)
            result = sorter(data)
            print(f"{original}  ->  {result}")
            assert result == sorted(original), "wrong result"
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
