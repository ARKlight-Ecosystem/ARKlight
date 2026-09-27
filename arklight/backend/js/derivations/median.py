"""
`median` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

One or more names: the middle value once sorted numerically, or the mean of
the two middle values for an even count.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("median", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "median"

JS_FRAGMENT = """    median: function (state, names, args) {
      var values = names.map(function (name) {
        return Number(state[name]) || 0;
      }).sort(function (a, b) {
        return a - b;
      });
      var mid = Math.floor(values.length / 2);
      return values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2;
    }"""
