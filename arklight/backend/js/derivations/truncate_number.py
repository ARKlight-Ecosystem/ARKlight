"""
`truncate_number` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

Single-name math transform: `Math.trunc` (drops the fractional part; named
`truncate_number` because a string `truncate` is a distinct, later entry).

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("truncate_number", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "truncate_number"

JS_FRAGMENT = """    truncate_number: function (state, names, args) {
      return Math.trunc(Number(state[names[0]]) || 0);
    }"""
