"""
Benchmark: Randomized Quicksort vs Deterministic Quicksort (first-element pivot).

MSCS-532 Assignment 3, Part 1.3.

Four experiments, each writing a CSV into results/:

  A. quicksort_times.csv        head-to-head wall-clock time, 4 required input
                                kinds plus an all-equal extra, both partition
                                schemes, n = 1,000 .. 8,000
  B. quicksort_scaling.csv      how the fast version scales to n = 320,000
                                (time / (n log2 n) should stay roughly flat)
  C. quicksort_comparisons.csv  counted comparisons against the formula
                                2(n+1)H_n - 4n from the analysis
  D. quicksort_pivot_luck.csv   how much one randomized run varies with pivot
                                luck alone (same input, 30 different seeds)

Run everything:       python benchmark_quicksort.py
Quick smoke test:     python benchmark_quicksort.py --quick
"""

import argparse
import csv
import gc
import math
import os
import platform
import random
import statistics
import sys
import time

from counting import CountingKey, get_count, reset_count
from randomized_quicksort import deterministic_quicksort, randomized_quicksort

RESULTS_DIR = "results"
DISTRIBUTIONS = ["random", "sorted", "reverse", "repeated", "all_equal"]
SCHEMES = ["lomuto", "three_way"]
ALGORITHMS = ["randomized", "deterministic"]
SEED = 532


def make_input(kind, n, rng):
    if kind == "random":
        return rng.sample(range(10 * n), n)  # distinct values, random order
    if kind == "sorted":
        return list(range(n))
    if kind == "reverse":
        return list(range(n, 0, -1))
    if kind == "repeated":
        return [rng.randrange(10) for _ in range(n)]  # only 10 distinct values
    if kind == "all_equal":
        return [7] * n
    raise ValueError(kind)


def make_sorter(algorithm, scheme, seed):
    if algorithm == "randomized":
        return lambda a: randomized_quicksort(a, rng=random.Random(seed), partition=scheme)
    return lambda a: deterministic_quicksort(a, partition=scheme)


def time_cell(sorter, data, max_trials, max_cell_seconds):
    """Median wall-clock seconds over several runs. Slow cells get fewer runs."""
    expected = sorted(data)
    times = []
    spent = 0.0
    while len(times) < max_trials and (not times or spent < max_cell_seconds):
        arr = list(data)
        gc.collect()
        start = time.perf_counter()
        sorter(arr)
        elapsed = time.perf_counter() - start
        if arr != expected:
            raise AssertionError("sort produced a wrong answer")
        times.append(elapsed)
        spent += elapsed
    return statistics.median(times), len(times)


def write_csv(name, header, rows):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  wrote {path}", file=sys.stderr)


def experiment_a(sizes, max_trials, max_cell_seconds):
    rows = []
    for dist in DISTRIBUTIONS:
        for n in sizes:
            data = make_input(dist, n, random.Random(SEED + n))
            for scheme in SCHEMES:
                for algo in ALGORITHMS:
                    sorter = make_sorter(algo, scheme, SEED)
                    secs, runs = time_cell(sorter, data, max_trials, max_cell_seconds)
                    rows.append([dist, scheme, algo, n, f"{secs:.6f}", runs])
                    print(f"  A {dist:9s} {scheme:9s} {algo:13s} n={n:<6d} {secs:9.4f}s ({runs} runs)",
                          file=sys.stderr, flush=True)
    write_csv("quicksort_times.csv", ["distribution", "partition", "algorithm", "n", "median_seconds", "runs"], rows)
    return rows


def experiment_b(sizes, max_trials, max_cell_seconds):
    rows = []
    for dist in ["random", "sorted", "reverse", "repeated", "all_equal"]:
        for n in sizes:
            data = make_input(dist, n, random.Random(SEED + n))
            sorter = make_sorter("randomized", "three_way", SEED)
            secs, runs = time_cell(sorter, data, max_trials, max_cell_seconds)
            per = secs / (n * math.log2(n)) * 1e6  # microseconds per n*log2(n)
            rows.append([dist, n, f"{secs:.6f}", f"{per:.5f}", runs])
            print(f"  B {dist:9s} n={n:<7d} {secs:8.4f}s  {per:.4f} us/(n log2 n)", file=sys.stderr, flush=True)
    write_csv("quicksort_scaling.csv", ["distribution", "n", "median_seconds", "us_per_n_log2_n", "runs"], rows)
    return rows


def count_comparisons(sorter, values):
    reset_count()
    arr = [CountingKey(v) for v in values]
    sorter(arr)
    assert [k.value for k in arr] == sorted(values)
    return get_count()


def expected_comparisons(n):
    """E[comparisons] of randomized Lomuto quicksort on n distinct keys: 2(n+1)H_n - 4n."""
    harmonic = sum(1.0 / k for k in range(1, n + 1))
    return 2 * (n + 1) * harmonic - 4 * n


def experiment_c(sizes, trials):
    rows = []
    for n in sizes:
        theory = expected_comparisons(n)
        n_log_n = n * math.log2(n)
        for dist in ("random", "sorted"):
            counts = []
            for t in range(trials):
                values = make_input(dist, n, random.Random(SEED * 7 + n + t))
                sorter = make_sorter("randomized", "lomuto", SEED + t)
                counts.append(count_comparisons(sorter, values))
            mean = statistics.mean(counts)
            rows.append(["randomized", dist, n, f"{mean:.1f}", f"{statistics.pstdev(counts):.1f}", f"{theory:.1f}",
                         f"{mean / theory:.4f}", f"{mean / n_log_n:.4f}", trials])
            print(f"  C randomized lomuto {dist:6s} n={n:<5d} mean={mean:10.1f} theory={theory:10.1f} ratio={mean / theory:.3f}",
                  file=sys.stderr, flush=True)
        # Deterministic on sorted input is exactly n(n-1)/2.
        values = make_input("sorted", n, random.Random(0))
        count = count_comparisons(make_sorter("deterministic", "lomuto", 0), values)
        rows.append(["deterministic", "sorted", n, f"{count:.1f}", "0.0", f"{n * (n - 1) / 2:.1f}",
                     f"{count / (n * (n - 1) / 2):.4f}", f"{count / n_log_n:.4f}", 1])
        print(f"  C deterministic lomuto sorted n={n:<5d} count={count} n(n-1)/2={n * (n - 1) // 2}", file=sys.stderr, flush=True)
        # Deterministic three-way on sorted input: not quadratic, but it grows faster than n log n.
        count3 = count_comparisons(make_sorter("deterministic", "three_way", 0), values)
        rows.append(["deterministic_three_way", "sorted", n, f"{count3:.1f}", "0.0", "", "",
                     f"{count3 / n_log_n:.4f}", 1])
        print(f"  C deterministic three-way sorted n={n:<5d} count={count3}", file=sys.stderr, flush=True)
        # Three-way partition on random input: no closed-form formula here, so
        # the last two columns just compare it with n log2 n.
        counts = []
        for t in range(trials):
            values = make_input("random", n, random.Random(SEED * 7 + n + t))
            counts.append(count_comparisons(make_sorter("randomized", "three_way", SEED + t), values))
        mean = statistics.mean(counts)
        rows.append(["randomized_three_way", "random", n, f"{mean:.1f}", f"{statistics.pstdev(counts):.1f}", "",
                     "", f"{mean / n_log_n:.4f}", trials])
        lomuto_random = next(r for r in reversed(rows) if r[0] == "randomized" and r[1] == "random" and r[2] == n)
        print(f"  C randomized three-way random n={n:<5d} mean={mean:10.1f}  = {mean / n_log_n:.3f} x n log2 n "
              f"(lomuto on the same kind of input: {lomuto_random[3]} = {float(lomuto_random[3]) / n_log_n:.3f} x n log2 n)",
              file=sys.stderr, flush=True)
    write_csv("quicksort_comparisons.csv",
              ["algorithm", "input", "n", "mean_comparisons", "std_dev", "formula", "mean_over_formula",
               "mean_over_n_log2_n", "trials"], rows)
    return rows


def experiment_d(sizes, seeds):
    """How much does ONE run of the randomized sort vary with pivot luck alone?

    Experiments A and B reuse seed 532 for every run, so the "median of 5 runs"
    there averages timing noise but not pivot luck. Here the input is fixed and
    only the seed changes: one timed run and one comparison count per seed.
    """
    rows = []
    for n in sizes:
        data = make_input("random", n, random.Random(SEED + n))
        for scheme in SCHEMES:
            times, counts = [], []
            for t in range(seeds):
                sorter = make_sorter("randomized", scheme, SEED + 100 + t)
                arr = list(data)
                gc.collect()
                start = time.perf_counter()
                sorter(arr)
                times.append(time.perf_counter() - start)
                assert arr == sorted(data)
                # the sorter builds its own random.Random(seed) on every call,
                # so this counting run sees exactly the same pivots as the timed run
                counts.append(count_comparisons(sorter, data))
            det_secs, _ = time_cell(make_sorter("deterministic", scheme, 0), data, 5, 15.0)
            mean_t = statistics.mean(times)
            rows.append([scheme, n, seeds, f"{mean_t:.6f}", f"{statistics.pstdev(times):.6f}",
                         f"{min(times):.6f}", f"{max(times):.6f}", f"{statistics.mean(counts):.1f}",
                         f"{statistics.pstdev(counts):.1f}", f"{det_secs:.6f}"])
            print(f"  D {scheme:9s} n={n:<5d} {seeds} seeds: time mean {mean_t * 1e3:.2f} ms, "
                  f"std {statistics.pstdev(times) / mean_t * 100:.1f}% (min {min(times) * 1e3:.2f}, max {max(times) * 1e3:.2f}); "
                  f"comparisons std {statistics.pstdev(counts) / statistics.mean(counts) * 100:.1f}%; "
                  f"deterministic {det_secs * 1e3:.2f} ms", file=sys.stderr, flush=True)
    write_csv("quicksort_pivot_luck.csv",
              ["partition", "n", "seeds", "mean_seconds", "std_seconds", "min_seconds", "max_seconds",
               "mean_comparisons", "std_comparisons", "deterministic_seconds"], rows)
    return rows


def write_environment():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "environment.txt"), "w") as f:
        f.write(f"python {sys.version}\n")
        f.write(f"platform {platform.platform()}\n")
        f.write(f"machine {platform.machine()}  processor {platform.processor()}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="tiny sizes, finishes in a few seconds")
    parser.add_argument("--only", choices=["a", "b", "c", "d"], help="run just one experiment")
    args = parser.parse_args()

    global RESULTS_DIR
    if args.quick:
        RESULTS_DIR = "results_quick"  # keep smoke-test output away from the real results
        a_sizes, b_sizes, c_sizes, trials, cell = [200, 400], [2000, 4000], [200, 400], 2, 2.0
    else:
        a_sizes = [1000, 2000, 4000, 8000]
        b_sizes = [10_000, 20_000, 40_000, 80_000, 160_000, 320_000]
        c_sizes = [500, 1000, 2000, 4000]
        trials, cell = 5, 15.0

    write_environment()
    if args.only in (None, "a"):
        print("Experiment A: head-to-head times", file=sys.stderr)
        experiment_a(a_sizes, trials, cell)
    if args.only in (None, "b"):
        print("Experiment B: scaling of randomized quicksort (three-way)", file=sys.stderr)
        experiment_b(b_sizes, trials, cell)
    if args.only in (None, "c"):
        print("Experiment C: comparison counts vs formula", file=sys.stderr)
        experiment_c(c_sizes, 20 if not args.quick else 5)
    if args.only in (None, "d"):
        print("Experiment D: how much one run varies with pivot luck alone", file=sys.stderr)
        experiment_d([200, 400] if args.quick else [1000, 8000], 5 if args.quick else 30)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
