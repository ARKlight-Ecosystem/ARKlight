"""
`divide` derivation fragment (`v0.061`, JS vocabulary addendum stage
1/10 -- see `docs/version history/v0.061.md`). See `sum.py` for the
general shape, and `subtract.py` for why name order matters here too:
`names[0]` is the starting value, and every subsequent name divides
it in declared order -- `Derive.divide("total", "count")` reads as
`total / count`. Division by a zero-coercing name follows JavaScript's
own float division semantics (`x / 0` is `Infinity`/`-Infinity`/`NaN`,
never a thrown error) -- `arklight.ir.build._evaluate_derivation`'s
`"divide"` case mirrors that explicitly (Python's `/` raises
`ZeroDivisionError` instead, so it can't be reused as-is) to keep the
build-time initial value and the client recompute in agreement even
at this edge case, same discipline `_coerce_number`'s own docstring
describes for `sum`/`multiply`.
"""

from __future__ import annotations

NAME = "divide"

JS_FRAGMENT = """    divide: function (state, names, args) {
      return names.slice(1).reduce(function (total, name) {
        return total / (Number(state[name]) || 0);
      }, Number(state[names[0]]) || 0);
    }"""
