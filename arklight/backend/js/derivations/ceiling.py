"""
`ceiling` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

Single-name math transform: `Math.ceil`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("ceiling", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "ceiling"

JS_FRAGMENT = """    ceiling: function (state, names, args) {
      return Math.ceil(Number(state[names[0]]) || 0);
    }"""
