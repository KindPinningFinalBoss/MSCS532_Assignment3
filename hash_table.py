"""
Hash table with chaining and universal hashing.

MSCS-532 Assignment 3, Part 2.

Collisions are handled by chaining: each slot holds a singly linked list of the
keys that hashed there. The hash function is picked at random from the
universal family

    h(k) = ((a * k + b) mod p) mod m        p prime, 1 <= a < p, 0 <= b < p

so for any two different integers k and l below p, the chance (over the random
a and b) that they land in the same slot is at most 1/m. That is the guarantee
the analysis in REPORT.md leans on.

The one catch: Python's built-in hash() turns any hashable key into an integer
first, and that integer is reduced mod p. The 1/m guarantee therefore holds for
keys whose hash() values are DIFFERENT mod p. Two keys whose hash() values are
equal mod p collide for every choice of a and b, and nothing in this module can
fix that. For example, in CPython hash(-1) == hash(-2) == -2, so the keys -1 and
-2 always share a slot (a test documents this). Strings are hashed with a
per-process random salt, so the chain layout for string keys can differ from one
run to the next.

The table doubles when the load factor (items / slots) goes above
max_load_factor and halves when it drops below min_load_factor, never going
under the starting capacity. It halves at most once per delete, so after a big
run of deletes it can take a few more deletes to reach the minimum. Each rebuild
picks a fresh random hash function.

min_load_factor must be at most max_load_factor / 4. After a doubling the load
is about max/2, and after a halving it is about 2 * min, so with this rule at
least a constant fraction of the table's size in inserts or deletes has to
happen before the next rebuild. That is what makes the cost of rebuilding O(1)
amortized per operation. With min close to max (say 0.9 and 1.0) a table
sitting near the boundary rebuilds on almost every operation: the constructor
rejects those settings.
"""

import random

# 2**61 - 1 is a Mersenne prime. Every hash() value is reduced mod p before it
# is used, so the keys the family sees are always in the range 0 .. p - 1.
PRIME = (1 << 61) - 1

_MISSING = object()


class UniversalHash:
    """One randomly chosen member of the family ((a*k + b) mod p) mod m."""

    __slots__ = ("m", "a", "b")

    def __init__(self, m, rng=None):
        if m < 1:
            raise ValueError("table size m must be at least 1")
        pick = rng if rng is not None else random
        self.m = m
        self.a = pick.randrange(1, PRIME)
        self.b = pick.randrange(0, PRIME)

    def __call__(self, key):
        x = hash(key) % PRIME
        return ((self.a * x + self.b) % PRIME) % self.m


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next_node):
        self.key = key
        self.value = value
        self.next = next_node


class HashTable:
    """Hash table with chaining. Supports insert, search and delete.

    initial_capacity  number of slots to start with (and the smallest the
                      table will ever shrink to)
    max_load_factor   grow (double) when items / slots goes above this
    min_load_factor   shrink (halve) when items / slots drops below this.
                      Defaults to max_load_factor / 4 and may not be larger
                      than that (see the module docstring for why)
    resize            set to False to keep the slot count fixed, which the
                      benchmarks use to show what resizing buys you
    rng               a random.Random for reproducible runs; defaults to the
                      random module
    """

    def __init__(
        self,
        initial_capacity=8,
        max_load_factor=1.0,
        min_load_factor=None,
        resize=True,
        rng=None,
    ):
        if initial_capacity < 1:
            raise ValueError("initial_capacity must be at least 1")
        if max_load_factor <= 0:
            raise ValueError("max_load_factor must be positive")
        if min_load_factor is None:
            min_load_factor = max_load_factor / 4
        if not 0 <= min_load_factor <= max_load_factor / 4:
            raise ValueError(
                "min_load_factor must be between 0 and max_load_factor / 4 "
                f"(got min={min_load_factor}, max={max_load_factor}); a larger value "
                "makes the table rebuild on almost every operation"
            )
        self._rng = rng if rng is not None else random
        self.max_load_factor = max_load_factor
        self.min_load_factor = min_load_factor
        self.resize = resize
        self._min_capacity = initial_capacity
        self.capacity = initial_capacity
        self._buckets = [None] * initial_capacity
        self._hash = UniversalHash(initial_capacity, self._rng)
        self._size = 0
        # Counters the benchmarks read.
        self.comparisons = 0  # key comparisons made while walking chains
        self.resize_count = 0  # how many times the table was rebuilt
        self.rehash_moves = 0  # items moved during all those rebuilds

    # ---- the three required operations ---------------------------------

    def insert(self, key, value):
        """Add key -> value. If key is already there, replace its value.

        Walking the chain to look for an existing key costs the same as an
        unsuccessful search, so the expected cost is Theta(1 + load factor).
        """
        idx = self._hash(key)
        node = self._buckets[idx]
        while node is not None:
            self.comparisons += 1
            if node.key == key:
                node.value = value
                return
            node = node.next
        # New key: link it in at the head of the chain, which is O(1).
        self._buckets[idx] = _Node(key, value, self._buckets[idx])
        self._size += 1
        if self.resize and self._size > self.max_load_factor * self.capacity:
            self._rebuild(self.capacity * 2)

    def search(self, key, default=None):
        """Return the value stored for key, or default if key is not present."""
        node = self._buckets[self._hash(key)]
        while node is not None:
            self.comparisons += 1
            if node.key == key:
                return node.value
            node = node.next
        return default

    def delete(self, key):
        """Remove key. Returns True if it was there, False if it was not."""
        idx = self._hash(key)
        prev = None
        node = self._buckets[idx]
        while node is not None:
            self.comparisons += 1
            if node.key == key:
                if prev is None:
                    self._buckets[idx] = node.next
                else:
                    prev.next = node.next
                self._size -= 1
                if (
                    self.resize
                    and self.capacity > self._min_capacity
                    and self._size < self.min_load_factor * self.capacity
                ):
                    self._rebuild(max(self._min_capacity, self.capacity // 2))
                return True
            prev = node
            node = node.next
        return False

    # ---- resizing -------------------------------------------------------

    def _rebuild(self, new_capacity):
        """Move every item into a table of new_capacity slots, new hash function."""
        old_buckets = self._buckets
        self.capacity = new_capacity
        self._buckets = [None] * new_capacity
        self._hash = UniversalHash(new_capacity, self._rng)
        self.resize_count += 1
        for node in old_buckets:
            while node is not None:
                following = node.next
                idx = self._hash(node.key)
                node.next = self._buckets[idx]
                self._buckets[idx] = node
                self.rehash_moves += 1
                node = following

    # ---- dict-style conveniences and inspection ------------------------

    @property
    def load_factor(self):
        return self._size / self.capacity

    def __len__(self):
        return self._size

    def __contains__(self, key):
        return self.search(key, _MISSING) is not _MISSING

    def __getitem__(self, key):
        value = self.search(key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        self.insert(key, value)

    def __delitem__(self, key):
        if not self.delete(key):
            raise KeyError(key)

    def chain_lengths(self):
        """Length of the chain in every slot (empty slots count as 0)."""
        lengths = []
        for node in self._buckets:
            n = 0
            while node is not None:
                n += 1
                node = node.next
            lengths.append(n)
        return lengths

    def max_chain_length(self):
        return max(self.chain_lengths())
