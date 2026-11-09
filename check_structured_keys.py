"""
Side check for REPORT.md, section 2.3.

Universal hashing promises a good AVERAGE over the random choice of the hash
function, not a good result for every single choice. This script inserts the
keys 0, m, 2m, 3m, ... (all multiples of the table size, the worst case for the
plain function h(k) = k mod m) into 2,000 separate tables, each with its own
random hash function, and looks at the spread of the average successful-search
cost.

Run:  python check_structured_keys.py      (about 10 seconds)
Output: printed, and saved to results/structured_keys.txt
"""

import math
import os
import random
import statistics

from hash_table import HashTable

M = N = 1000  # load factor 1
TABLES = 2000

keys = [M * i for i in range(N)]
costs = []
for t in range(TABLES):
    table = HashTable(initial_capacity=M, max_load_factor=1e9, resize=False, rng=random.Random(10_000 + t))
    for k in keys:
        table.insert(k, k)
    table.comparisons = 0
    for k in keys:
        table.search(k)
    costs.append(table.comparisons / N)

costs.sort()
bound = 1 + (N - 1) / (2 * M)
stderr = statistics.stdev(costs) / math.sqrt(TABLES)
lines = [
    f"{TABLES} tables, {N} keys, {M} slots, keys are all multiples of {M}",
    f"mean comparisons per successful search : {statistics.mean(costs):.3f}   "
    f"(standard error {stderr:.3f}; bound 1 + (n-1)/(2m) = {bound:.3f})",
    f"median table                           : {statistics.median(costs):.3f}",
    f"5th / 95th percentile table            : {costs[int(0.05 * TABLES)]:.3f} / {costs[int(0.95 * TABLES)]:.3f}",
    f"best / worst table                     : {costs[0]:.3f} / {costs[-1]:.3f}",
    f"tables that cost more than 2x the bound: {sum(c > 2 * bound for c in costs)}",
]
print("\n".join(lines))
os.makedirs("results", exist_ok=True)
with open(os.path.join("results", "structured_keys.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
