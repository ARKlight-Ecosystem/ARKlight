"""
`sqrt` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

Single-name math transform: `Math.sqrt` (`NaN` for a negative input, never a
thrown error).

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("sqrt", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "sqrt"

JS_FRAGMENT = """    sqrt: function (state, names, args) {
      return Math.sqrt(Number(state[names[0]]) || 0);
    }"""
