"""
`power` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

Exactly two names, in order: `names[0]` is the base, `names[1]` the
exponent -- `Derive.power("base", "exponent")` reads as `base ** exponent`.
`Math.pow`, including its `pow(1, Infinity) === NaN` departure from C's
`pow`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("power", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "power"

JS_FRAGMENT = """    power: function (state, names, args) {
      return Math.pow(
        Number(state[names[0]]) || 0,
        Number(state[names[1]]) || 0
      );
    }"""
