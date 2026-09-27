"""
`average` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

One or more names: the arithmetic mean, summed left to right and divided by
the count of names (`Derive.mean` is an alias for this kind).

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("average", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "average"

JS_FRAGMENT = """    average: function (state, names, args) {
      var values = names.map(function (name) {
        return Number(state[name]) || 0;
      });
      return values.reduce(function (total, value) {
        return total + value;
      }, 0) / values.length;
    }"""
