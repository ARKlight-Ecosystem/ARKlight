"""
`subtract` derivation fragment (`v0.061`, JS vocabulary addendum stage
1/10 -- see `docs/version history/v0.061.md`). See `sum.py` for the
general shape.

Unlike `sum`/`multiply`, `subtract` isn't associative, so name order
matters: `names[0]` is the starting value, and every subsequent name
is subtracted from it in declared order -- `Derive.subtract("total",
"discount")` reads as `total - discount`, not the other way round.
Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("subtract", ...)` case so a page's server-rendered `Bind(...)` text
never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "subtract"

JS_FRAGMENT = """    subtract: function (state, names, args) {
      return names.slice(1).reduce(function (total, name) {
        return total - (Number(state[name]) || 0);
      }, Number(state[names[0]]) || 0);
    }"""
