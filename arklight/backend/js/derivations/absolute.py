"""
`absolute` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

Single-name math transform: `Math.abs`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("absolute", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "absolute"

JS_FRAGMENT = """    absolute: function (state, names, args) {
      return Math.abs(Number(state[names[0]]) || 0);
    }"""
