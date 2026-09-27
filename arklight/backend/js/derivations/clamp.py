"""
`clamp` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

Exactly three names, in order: value, lower bound, upper bound --
`Derive.clamp("x", "lo", "hi")` reads as `min(max(x, lo), hi)`. No direct
JavaScript built-in; the composition is the whole definition, so a lower
bound above the upper bound yields the upper bound.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("clamp", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "clamp"

JS_FRAGMENT = """    clamp: function (state, names, args) {
      return Math.min(
        Math.max(Number(state[names[0]]) || 0, Number(state[names[1]]) || 0),
        Number(state[names[2]]) || 0
      );
    }"""
