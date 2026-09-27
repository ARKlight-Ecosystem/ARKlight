"""
`log10` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

Single-name math transform: `Math.log10`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("log10", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "log10"

JS_FRAGMENT = """    log10: function (state, names, args) {
      return Math.log10(Number(state[names[0]]) || 0);
    }"""
