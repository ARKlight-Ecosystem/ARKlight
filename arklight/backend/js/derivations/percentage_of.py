"""
`percentage_of` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

Exactly two names, in order: `Derive.percentage_of("done", "total")` reads
as `(done / total) * 100`. Division by zero follows JavaScript's float
semantics (`Infinity`/`NaN`), same as `divide`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("percentage_of", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "percentage_of"

JS_FRAGMENT = """    percentage_of: function (state, names, args) {
      return ((Number(state[names[0]]) || 0) / (Number(state[names[1]]) || 0)) * 100;
    }"""
