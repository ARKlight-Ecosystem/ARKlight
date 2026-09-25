"""
`midpoint` derivation fragment (`v0.068`, JS vocabulary addendum
stage 8/10 -- see `docs/version history/v0.068.md`). See `sum.py` for
the general shape.

Exactly two names: `Derive.midpoint("a", "b")` reads as C++20
`std::midpoint(a, b)` -- `a + (b - a) / 2` rather than the naive
`(a + b) / 2`, so a pair of very large same-sign values never round
through an intermediate sum that overflows before the division does.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("midpoint", ...)` case (via `arklight/ir/js_numeric.py`'s
`js_midpoint`) so a page's server-rendered `Bind(...)` text never
disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "midpoint"

JS_FRAGMENT = """    midpoint: function (state, names, args) {
      var a = Number(state[names[0]]) || 0;
      var b = Number(state[names[1]]) || 0;
      return a + (b - a) / 2;
    }"""
