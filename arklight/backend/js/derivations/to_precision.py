"""
`to_precision` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

One name plus a `digits` argument (1-100, validated at build time):
`Number.prototype.toPrecision(digits)`. Returns a **string**, in
exponent notation (`"1.23e+5"`) when the exponent is below -6 or at least
`digits`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("to_precision", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "to_precision"

JS_FRAGMENT = """    to_precision: function (state, names, args) {
      return (Number(state[names[0]]) || 0).toPrecision(args.digits);
    }"""
