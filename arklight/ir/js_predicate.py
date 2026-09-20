"""
Build-time mirrors of the `v0.066` predicates catalog (JS vocabulary
addendum stage 6/10 -- see `docs/version history/v0.066.md`).

`Show(...)` pre-renders its `hidden` attribute at build time against the
page's *initial* state (`arklight/backend/html/page_render.py`), and the
client's `arkEvalPredicate` (`arklight/backend/js/runtime/show.py`) then
keeps it in sync after every state change. Both halves must reach the
same verdict for the same state, or a page flashes the wrong content the
moment its script runs. Python's own notion of truthiness, equality and
emptiness differs from JavaScript's in exactly the places that matter
here, so each new predicate kind is written out below against JavaScript's
rules, the same job `js_string.py`/`js_numeric.py` do for the derivation
catalogs:

* Truthiness: `NaN` is falsy in JS but truthy in Python's `bool(...)`;
  an empty array/object is truthy in JS but falsy in Python.
* Equality (`one_of`): JS `indexOf` is strict -- `1 === true` is false,
  where Python's `1 == True` is true.
* Numbers (`in_range`): `Number(x) || 0`, via `build._coerce_number`,
  exactly as `Derive.clamp` reads them.

The pre-existing `truthy`/`falsy` kinds are deliberately not routed
through here; they keep using Python's `bool(...)`, unchanged.
"""

from __future__ import annotations

import math
from typing import Any, Callable

from arklight.ir.build import _coerce_number


def js_truthy(value: Any) -> bool:
    """JavaScript's `!!value` for the value types `State(...)` can hold."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return not (value == 0 or (isinstance(value, float) and math.isnan(value)))
    if isinstance(value, str):
        return len(value) > 0
    # Arrays and objects are always truthy in JS, even when empty.
    return True


def js_is_null(value: Any) -> bool:
    """`value === null || value === undefined`. A `State(...)` name that
    was never given a value reads back as `None` here, and `undefined`
    in the browser."""
    return value is None


def js_is_empty(value: Any) -> bool:
    """`null`/`undefined`, a zero-length string, or a zero-length array.
    Everything else -- `0`, `false`, an object -- is *not* empty.

    Differs on purpose from `Derive.is_empty` (v0.065), which reads
    `String(x).length === 0`: there `None` is the text `"null"`, so not
    empty. As a `Show` guard, "no value yet" is the case people mean.
    """
    if value is None:
        return True
    if isinstance(value, (str, list, tuple)):
        return len(value) == 0
    return False


def _strict_equal(a: Any, b: Any) -> bool:
    """`a === b` for JSON scalars: no coercion between types, and a
    boolean is never a number (Python would say `True == 1`)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    return a is None and b is None


def js_one_of(value: Any, values: list[Any]) -> bool:
    """`values.indexOf(value) !== -1`."""
    return any(_strict_equal(value, candidate) for candidate in values)


def js_in_range(value: Any, low: Any, high: Any) -> bool:
    """`lo <= x <= hi` over `Number(x) || 0`, both ends inclusive. A
    `low` above `high` matches nothing (unlike `clamp`, which returns
    its upper bound)."""
    x, lo, hi = (_coerce_number(v) for v in (value, low, high))
    return lo <= x <= hi


def _and(names, args, get) -> bool:
    return all(js_truthy(get(name)) for name in names)


def _or(names, args, get) -> bool:
    return any(js_truthy(get(name)) for name in names)


# kind -> evaluator(names, args, get), where `get(name)` reads the page's
# initial value for a state/computed name.
PREDICATE_EVALUATORS: dict[str, Callable[..., bool]] = {
    "and": _and,
    "or": _or,
    "not": lambda names, args, get: not js_truthy(get(names[0])),
    "in_range": lambda names, args, get: js_in_range(*(get(n) for n in names)),
    "one_of": lambda names, args, get: js_one_of(get(names[0]), args["values"]),
    "is_empty": lambda names, args, get: js_is_empty(get(names[0])),
    "is_not_empty": lambda names, args, get: not js_is_empty(get(names[0])),
    "is_null": lambda names, args, get: js_is_null(get(names[0])),
}
