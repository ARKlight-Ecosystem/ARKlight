"""
`to_fixed` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

One name plus a `digits` argument (0-100, validated at build time):
`Number.prototype.toFixed(digits)`. Returns a **string** -- the intended
use is display (`Derive.to_fixed("price", 2)` -> `"9.50"`), not further
arithmetic.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("to_fixed", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "to_fixed"

JS_FRAGMENT = """    to_fixed: function (state, names, args) {
      return (Number(state[names[0]]) || 0).toFixed(args.digits);
    }"""
