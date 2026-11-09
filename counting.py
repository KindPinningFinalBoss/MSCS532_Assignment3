"""
Comparison counter used by the tests and the benchmarks.

Wrapping each value in CountingKey lets us count how many times a sort
compares two elements without touching the sorting code itself. The count is
kept in one module-level variable, so call reset_count() before each run.
"""

_count = 0


def reset_count():
    global _count
    _count = 0


def get_count():
    return _count


class CountingKey:
    """A value that adds one to the global count every time it is compared."""

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        global _count
        _count += 1
        return self.value < other.value

    def __le__(self, other):
        global _count
        _count += 1
        return self.value <= other.value

    def __gt__(self, other):
        global _count
        _count += 1
        return self.value > other.value

    def __ge__(self, other):
        global _count
        _count += 1
        return self.value >= other.value

    def __repr__(self):
        return f"CountingKey({self.value!r})"
