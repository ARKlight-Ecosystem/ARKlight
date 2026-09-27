"""
`hypot` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

One or more names: the Euclidean norm `sqrt(a**2 + b**2 + ...)`, via
`Math.hypot`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("hypot", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "hypot"

JS_FRAGMENT = """    hypot: function (state, names, args) {
      return Math.hypot.apply(null, names.map(function (name) {
        return Number(state[name]) || 0;
      }));
    }"""
