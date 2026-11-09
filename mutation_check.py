"""
Break the code on purpose and check that the tests notice.

Each "mutant" is a temporary copy of the source with ONE small deliberate bug
(a wrong pivot, an off-by-one, a counter that is never updated, a missing
guard ...). The unit tests are run against that copy. A good test suite fails
on every mutant. A mutant the tests miss ("SURVIVED") means either a gap in the
tests or a change that does not alter behaviour.

Nothing in the real source files is touched: the work happens in a temp folder.

Run:   python mutation_check.py          (about a minute)
Output: printed, and saved to results/mutation_check.txt
"""

import os
import shutil
import subprocess
import sys
import tempfile

# (name, file, exact text to replace (must occur once), replacement)
MUTANTS = [
    # --- quicksort ---------------------------------------------------------
    ("deterministic pivot is the last element", "randomized_quicksort.py",
     "lambda lo, hi: lo", "lambda lo, hi: hi"),
    ("three-way scan skips re-checking the swapped element", "randomized_quicksort.py",
     "gt -= 1", "gt -= 1; i += 1"),
    ("Lomuto loop stops one element early", "randomized_quicksort.py",
     "for j in range(lo, hi):", "for j in range(lo, hi - 1):"),
    ("recurses into the BIGGER side", "randomized_quicksort.py",
     "if lt - lo < hi - gt:", "if lt - lo > hi - gt:"),
    ("randomized pivot is always the first element", "randomized_quicksort.py",
     "pick = (rng if rng is not None else random).randint", "pick = lambda lo, hi: lo"),
    ("comparison counter never counts <", "counting.py",
     "def __lt__(self, other):\n        global _count\n        _count += 1\n",
     "def __lt__(self, other):\n        global _count\n"),
    # --- hash table --------------------------------------------------------
    ("hash function always returns slot 0", "hash_table.py",
     "return ((self.a * x + self.b) % PRIME) % self.m", "return 0"),
    ("hash function is plain k mod m (not universal)", "hash_table.py",
     "return ((self.a * x + self.b) % PRIME) % self.m", "return x % self.m"),
    ("delete forgets to lower the size", "hash_table.py",
     "                self._size -= 1\n", "                pass\n"),
    ("table never grows", "hash_table.py",
     "self._rebuild(self.capacity * 2)", "pass"),
    ("table grows by one slot instead of doubling", "hash_table.py",
     "self._rebuild(self.capacity * 2)", "self._rebuild(self.capacity + 1)"),
    ("inserting an existing key does not replace its value", "hash_table.py",
     "                node.value = value\n", "                pass\n"),
    ("rebuild never counts moved items", "hash_table.py",
     "                self.rehash_moves += 1\n", "                pass\n"),
    ("rebuild reuses a fixed seed instead of the table's rng", "hash_table.py",
     "self._hash = UniversalHash(new_capacity, self._rng)",
     "self._hash = UniversalHash(new_capacity, random.Random(0))"),
    ("shrink guard dropped (rebuilds at the minimum size)", "hash_table.py",
     "                    and self.capacity > self._min_capacity\n", ""),
    ("table never shrinks", "hash_table.py",
     "and self._size < self.min_load_factor * self.capacity", "and self._size < 0"),
    ("constructor allows min_load_factor up to max_load_factor", "hash_table.py",
     "if not 0 <= min_load_factor <= max_load_factor / 4:", "if not 0 <= min_load_factor <= max_load_factor:"),
    ("default min_load_factor is a fixed 0.25", "hash_table.py",
     "min_load_factor = max_load_factor / 4\n        if not", "min_load_factor = 0.25\n        if not"),
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    lines = [f"mutation check: {len(MUTANTS)} deliberate bugs, python {sys.version.split()[0]}"]
    survivors = []
    for name, filename, old, new in MUTANTS:
        with tempfile.TemporaryDirectory() as tmp:
            for f in os.listdir(here):
                if f.endswith(".py") and f != "mutation_check.py":
                    shutil.copy(os.path.join(here, f), tmp)
            path = os.path.join(tmp, filename)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if text.count(old) != 1:
                lines.append(f"[?]        {name}: could not apply (the text to change appears {text.count(old)} times)")
                continue
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text.replace(old, new))
            try:
                result = subprocess.run([sys.executable, "-m", "unittest"], cwd=tmp,
                                        capture_output=True, text=True, timeout=180)
                caught = result.returncode != 0
                detail = [l for l in (result.stderr + result.stdout).strip().splitlines() if l.strip()][-1]
            except subprocess.TimeoutExpired:
                caught, detail = True, "timed out (an endless loop or a very slow run counts as caught)"
        lines.append(f"[{'caught' if caught else 'SURVIVED'}]  {name}   ({detail})")
        if not caught:
            survivors.append(name)
        print(lines[-1], flush=True)
    lines.append("")
    lines.append(f"{len(MUTANTS) - len(survivors)} of {len(MUTANTS)} caught." +
                 (f" Survivors: {survivors}" if survivors else ""))
    print(lines[-1])
    os.makedirs(os.path.join(here, "results"), exist_ok=True)
    with open(os.path.join(here, "results", "mutation_check.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
