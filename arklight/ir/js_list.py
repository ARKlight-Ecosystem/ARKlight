"""
Python mirrors of the JavaScript array semantics the list-scalar
derivation catalog (`v0.067`, JS vocabulary addendum stage 7/10 -- see
`docs/version history/v0.067.md`) depends on.

Same reason `arklight/ir/js_numeric.py` and `arklight/ir/js_string.py`
exist for their catalogs: `arklight.ir.build`'s `_evaluate_derivation`
pre-renders a `Computed(...)`'s initial value at build time, and the
browser recomputes it from the shipped fragments on the first state
change. The two must agree. Every function here takes the *raw* state
value (whatever `get(name)` returned) and reproduces what the matching
fragment in `arklight/backend/js/derivations/list_*.py` returns for it.

Three rules are shared by the whole catalog:

* **A value that isn't a list reads as an empty list.** `Array.isArray`
  is the test on the client, so a string, a number, an object, `None`
  and a name that was never given a value all behave like `[]`.
  (`Derive.count` is the one derivation that also measures strings and
  objects; `Derive.list_length` deliberately does not.)
* **Numeric kinds read each element as a number the way the math
  catalog reads a state value** -- `Number(x) || 0`, so `NaN` and `-0`
  become `+0` -- with one narrowing: only numbers, strings and booleans
  are read; `null`, a nested list and an object read as `0` (JavaScript
  would turn `[5]` into `5` through `Array.prototype.toString`, which is
  never what a caller means). `js_to_number` reproduces
  `Number(string)`'s own grammar rather than Python's `float()`, which
  accepts `"1_0"`, `"inf"`, `"nan"` and non-ASCII digits and does not
  accept `"0x10"`.
* **Equality is strict, and never mixes types** (`===`): `1 === true` is
  false where Python's `1 == True` is true, and a string is compared as
  UTF-16 code units, so an emoji equals its own surrogate pair.

Nothing here is a general evaluator: each function is one fixed, named
operation a registry entry points at, and `list_any`/`list_all` take
one of the six existing `compare` operators plus a literal, never a
callback.
"""

from __future__ import annotations

import math
import re
from typing import Any

from arklight.ir.js_string import JS_WHITESPACE, to_units

_INF = math.inf

# `Number(string)`'s `StrDecimalLiteral`: an optionally signed
# `Infinity`, or digits with an optional fraction and exponent. ASCII
# digits only -- Python's `\d` would also accept every other script's.
_DECIMAL_LITERAL = re.compile(
    r"[+-]?(?:Infinity|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\Z"
)
# `0x`/`0o`/`0b` integer literals -- unsigned, with at least one digit.
_RADIX_LITERAL = re.compile(r"0(?:[xX][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)\Z")
_RADIX_BASE = {"x": 16, "o": 8, "b": 2}


def _int_to_double(value: int) -> float:
    try:
        return float(value)
    except OverflowError:
        return _INF if value > 0 else -_INF


def _string_to_number(text: str) -> float:
    """`Number(text)` for a string: `NaN` when it is not a numeric
    literal. Surrounding JavaScript whitespace is ignored and an empty
    (or all-whitespace) string is `0`."""
    text = text.strip(JS_WHITESPACE)
    if text == "":
        return 0.0
    if _RADIX_LITERAL.match(text):
        return _int_to_double(int(text[2:], _RADIX_BASE[text[1].lower()]))
    if _DECIMAL_LITERAL.match(text):
        return float(text)
    return math.nan


def js_to_number(value: Any) -> float:
    """Read one list element as a number: `Number(x) || 0` for a number,
    a string or a boolean, and `0` for anything else (see the module
    docstring). Never `NaN`, never `-0`."""
    if isinstance(value, bool):
        number = 1.0 if value else 0.0
    elif isinstance(value, int):
        number = _int_to_double(value)
    elif isinstance(value, float):
        number = value
    elif isinstance(value, str):
        number = _string_to_number(value)
    else:
        return 0.0
    return 0.0 if (number == 0 or math.isnan(number)) else number


def _as_list(value: Any) -> list[Any]:
    """`Array.isArray(value) ? value : []` (a tuple is what a Python
    caller's list becomes once it is JSON-serialised, so it is a list)."""
    return list(value) if isinstance(value, (list, tuple)) else []


def _numbers(value: Any) -> list[float]:
    return [js_to_number(item) for item in _as_list(value)]


def js_strict_equal(a: Any, b: Any) -> bool:
    """`a === b` for the JSON values a list can hold. Numbers compare as
    the doubles JavaScript sees (so an integer past `2**53` rounds the
    way `JSON.parse` rounds it), strings as UTF-16 code units, and a
    boolean is never a number."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        x = _int_to_double(a) if isinstance(a, int) else a
        y = _int_to_double(b) if isinstance(b, int) else b
        return x == y
    if isinstance(a, str) and isinstance(b, str):
        return to_units(a) == to_units(b)
    return a is None and b is None


# ---------------------------------------------------------------------------
# One function per catalog entry.
# ---------------------------------------------------------------------------


def js_list_length(value: Any) -> int:
    """`Array.isArray(v) ? v.length : 0`."""
    return len(_as_list(value))


def js_list_min(value: Any) -> float:
    """The smallest element read as a number; `Infinity` for an empty
    list, exactly like `Math.min()` with no arguments."""
    return min(_numbers(value), default=_INF)


def js_list_max(value: Any) -> float:
    """The largest element read as a number; `-Infinity` for an empty
    list, exactly like `Math.max()` with no arguments."""
    return max(_numbers(value), default=-_INF)


def js_list_average(value: Any) -> float:
    """The arithmetic mean of the elements read as numbers, summed left
    to right (an explicit loop: since Python 3.12 `sum()` on floats is
    compensated and disagrees with JavaScript's plain `+=` in the last
    digit). `NaN` for an empty list (`0 / 0`)."""
    numbers = _numbers(value)
    total = 0.0
    for number in numbers:
        total += number
    if not numbers:
        return math.nan
    return total / len(numbers)


def js_list_first(value: Any) -> Any:
    """The first element as it is, or `None` (`null`) for an empty list."""
    items = _as_list(value)
    return items[0] if items else None


def js_list_last(value: Any) -> Any:
    """The last element as it is, or `None` (`null`) for an empty list."""
    items = _as_list(value)
    return items[-1] if items else None


def js_list_includes(value: Any, literal: Any) -> bool:
    """`Array.prototype.includes(literal)` over `===` equality."""
    return any(js_strict_equal(item, literal) for item in _as_list(value))


def _matches(item: Any, op: str, literal: Any) -> bool:
    """One element against the `compare` operator `op`. `eq`/`ne` are
    `===`/`!==` against the element itself; the four relational
    operators compare the element read as a number (`js_to_number`)
    against a numeric literal."""
    if op == "eq":
        return js_strict_equal(item, literal)
    if op == "ne":
        return not js_strict_equal(item, literal)
    number = js_to_number(item)
    if op == "gt":
        return number > literal
    if op == "lt":
        return number < literal
    if op == "gte":
        return number >= literal
    if op == "lte":
        return number <= literal
    return False  # unreachable once Validation has run


def js_list_any(value: Any, op: str, literal: Any) -> bool:
    """`Array.prototype.some` over one fixed comparison; `False` for an
    empty list."""
    return any(_matches(item, op, literal) for item in _as_list(value))


def js_list_all(value: Any, op: str, literal: Any) -> bool:
    """`Array.prototype.every` over one fixed comparison; `True` for an
    empty list (vacuous truth, as in JavaScript)."""
    return all(_matches(item, op, literal) for item in _as_list(value))
