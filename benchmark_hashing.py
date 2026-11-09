"""
Benchmark: hash table with chaining.

MSCS-532 Assignment 3, Part 2.2.

Three experiments, each writing a CSV into results/:

  H1. hash_load_factor.csv   average key comparisons in successful and
                             unsuccessful searches at several load factors,
                             against the formulas from the analysis
  H2. hash_scaling.csv       time per insert / search / delete as n grows,
                             with resizing on and with a fixed table
  H3. hash_max_load.csv      what different max_load_factor settings cost in
                             time and in table size

Run everything:       python benchmark_hashing.py
Quick smoke test:     python benchmark_hashing.py --quick
"""

import argparse
import csv
import gc
import math
import os
import random
import statistics
import sys
import time
import zlib

from hash_table import HashTable

RESULTS_DIR = "results"
SEED = 532


def write_csv(name, header, rows):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  wrote {path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# H1: comparisons vs load factor
# ---------------------------------------------------------------------------

def experiment_h1(m, alphas, tables_per_point, misses):
    """tables_per_point maps key kind -> how many independent tables to average.

    Structured keys (multiples of m) need many more tables than random keys:
    most random hash functions treat them very well, but a minority treat
    them badly, so a small average is noisy.
    """
    rows = []
    for key_kind in ("random", "multiples_of_m"):
        for alpha in alphas:
            n = int(alpha * m)
            hit_means, miss_means, max_chains = [], [], []
            # Every (key kind, load factor) row gets its OWN stream of hash functions, so the
            # rows are independent samples. (An earlier version reused the same functions in
            # every row, which made the rows move together.)
            row_seed = zlib.crc32(f"{key_kind}/{alpha}".encode()) * 10_007
            for t in range(tables_per_point[key_kind]):
                gen = random.Random(SEED + 1000 * t + n)
                table = HashTable(initial_capacity=m, max_load_factor=1e9, resize=False,
                                  rng=random.Random(row_seed + t))
                if key_kind == "random":
                    keys = gen.sample(range(10**9), n)
                    absent = gen.sample(range(10**9, 2 * 10**9), misses)
                else:
                    # Every key is a multiple of m: the worst case for h(k) = k mod m.
                    keys = [m * i for i in range(n)]
                    absent = [m * (n + 1 + i) for i in range(misses)]
                for k in keys:
                    table.insert(k, k)
                table.comparisons = 0
                for k in keys:
                    table.search(k)
                hit_means.append(table.comparisons / n)
                table.comparisons = 0
                for k in absent:
                    table.search(k)
                miss_means.append(table.comparisons / misses)
                max_chains.append(table.max_chain_length())
            hit_sorted = sorted(hit_means)
            tables = len(hit_means)
            rows.append([
                key_kind, alpha, n, m,
                f"{statistics.mean(hit_means):.4f}", f"{statistics.median(hit_means):.4f}",
                f"{hit_sorted[int(0.95 * (tables - 1))]:.4f}", f"{hit_sorted[-1]:.4f}",
                f"{1 + (n - 1) / (2 * m):.4f}",
                f"{statistics.mean(miss_means):.4f}", f"{n / m:.4f}",
                f"{statistics.mean(max_chains):.1f}", tables,
                f"{statistics.stdev(hit_means) / math.sqrt(tables):.4f}",
                f"{statistics.stdev(miss_means) / math.sqrt(tables):.4f}",
            ])
            print(f"  H1 {key_kind:15s} alpha={alpha:<5} hit mean={rows[-1][4]} median={rows[-1][5]} "
                  f"p95={rows[-1][6]} max={rows[-1][7]} (theory {rows[-1][8]})  "
                  f"miss={rows[-1][9]} (theory {rows[-1][10]})  mean max chain={rows[-1][11]}  [{tables} tables]",
                  file=sys.stderr, flush=True)
    write_csv("hash_load_factor.csv",
              ["keys", "alpha", "n", "m", "successful_mean", "successful_median", "successful_p95",
               "successful_max", "successful_theory", "unsuccessful_mean", "unsuccessful_theory",
               "mean_max_chain", "tables", "successful_stderr", "unsuccessful_stderr"], rows)


# ---------------------------------------------------------------------------
# H2: time per operation as n grows
# ---------------------------------------------------------------------------

def timed_run(make_table, keys, search_order, delete_order):
    table = make_table()
    gc.collect()
    t0 = time.perf_counter()
    for k in keys:
        table.insert(k, k)
    t1 = time.perf_counter()
    for k in search_order:
        table.search(k)
    t2 = time.perf_counter()
    stats = (table.capacity, table.resize_count, table.rehash_moves, table.load_factor, table.max_chain_length())
    for k in delete_order:
        table.delete(k)
    t3 = time.perf_counter()
    assert len(table) == 0
    n = len(keys)
    return (t1 - t0) / n * 1e6, (t2 - t1) / n * 1e6, (t3 - t2) / n * 1e6, stats


def experiment_h2(sizes, fixed_capacity, trials):
    rows = []
    modes = {
        "resizing_on": lambda: HashTable(initial_capacity=8, max_load_factor=1.0, rng=random.Random(SEED)),
        "fixed_table": lambda: HashTable(initial_capacity=fixed_capacity, resize=False, rng=random.Random(SEED)),
    }
    for n in sizes:
        gen = random.Random(SEED + n)
        keys = gen.sample(range(10**9), n)
        search_order = list(keys)
        gen.shuffle(search_order)
        delete_order = list(keys)
        gen.shuffle(delete_order)
        for mode, factory in modes.items():
            ins, sea, dele = [], [], []
            stats = None
            for _ in range(trials):
                i_us, s_us, d_us, stats = timed_run(factory, keys, search_order, delete_order)
                ins.append(i_us)
                sea.append(s_us)
                dele.append(d_us)
            cap, resizes, moves, lf, maxc = stats
            rows.append([mode, n, f"{statistics.median(ins):.4f}", f"{statistics.median(sea):.4f}",
                         f"{statistics.median(dele):.4f}", cap, resizes, moves,
                         f"{moves / n:.3f}", f"{lf:.3f}", maxc])
            print(f"  H2 {mode:12s} n={n:<7d} insert={rows[-1][2]}us search={rows[-1][3]}us delete={rows[-1][4]}us "
                  f"capacity={cap} load={lf:.2f} max chain={maxc}", file=sys.stderr, flush=True)
    write_csv("hash_scaling.csv",
              ["mode", "n", "insert_us", "search_us", "delete_us", "final_capacity", "resizes",
               "rehash_moves", "moves_per_insert", "final_load_factor", "final_max_chain"], rows)


# ---------------------------------------------------------------------------
# H3: effect of the max load factor setting
# ---------------------------------------------------------------------------

def experiment_h3(n, limits, trials):
    rows = []
    gen = random.Random(SEED + n)
    keys = gen.sample(range(10**9), n)
    search_order = list(keys)
    gen.shuffle(search_order)
    delete_order = list(keys)
    gen.shuffle(delete_order)
    for limit in limits:
        factory = lambda limit=limit: HashTable(initial_capacity=8, max_load_factor=limit,
                                                min_load_factor=min(0.25, limit / 4),
                                                rng=random.Random(SEED))
        ins, sea, dele = [], [], []
        stats = None
        for _ in range(trials):
            i_us, s_us, d_us, stats = timed_run(factory, keys, search_order, delete_order)
            ins.append(i_us)
            sea.append(s_us)
            dele.append(d_us)
        cap, resizes, moves, lf, maxc = stats
        rows.append([limit, n, f"{statistics.median(ins):.4f}", f"{statistics.median(sea):.4f}",
                     f"{statistics.median(dele):.4f}", cap, resizes, f"{moves / n:.3f}", f"{lf:.3f}", maxc])
        print(f"  H3 max_load={limit:<4} insert={rows[-1][2]}us search={rows[-1][3]}us delete={rows[-1][4]}us "
              f"slots={cap} load={lf:.2f} max chain={maxc}", file=sys.stderr, flush=True)
    write_csv("hash_max_load.csv",
              ["max_load_factor", "n", "insert_us", "search_us", "delete_us", "final_slots",
               "resizes", "moves_per_insert", "final_load_factor", "final_max_chain"], rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="tiny sizes, finishes in a few seconds")
    parser.add_argument("--only", choices=["h1", "h2", "h3"], help="run just one experiment")
    args = parser.parse_args()

    global RESULTS_DIR
    if args.quick:
        RESULTS_DIR = "results_quick"  # keep smoke-test output away from the real results
        h1 = dict(m=100, alphas=[0.5, 2], tables_per_point={"random": 2, "multiples_of_m": 4}, misses=200)
        h2 = dict(sizes=[500, 2000], fixed_capacity=128, trials=1)
        h3 = dict(n=5000, limits=[1.0, 4.0], trials=1)
    else:
        h1 = dict(m=1000, alphas=[0.25, 0.5, 1, 2, 4, 8],
                  tables_per_point={"random": 100, "multiples_of_m": 2000}, misses=5000)
        h2 = dict(sizes=[1000, 4000, 16000, 64000, 128000], fixed_capacity=1024, trials=5)
        h3 = dict(n=100_000, limits=[0.5, 1.0, 2.0, 4.0, 8.0], trials=5)

    if args.only in (None, "h1"):
        print("H1: comparisons vs load factor", file=sys.stderr)
        experiment_h1(**h1)
    if args.only in (None, "h2"):
        print("H2: time per operation vs n", file=sys.stderr)
        experiment_h2(**h2)
    if args.only in (None, "h3"):
        print("H3: effect of max load factor", file=sys.stderr)
        experiment_h3(**h3)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
