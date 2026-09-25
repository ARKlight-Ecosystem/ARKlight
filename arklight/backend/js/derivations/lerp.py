"""
`lerp` derivation fragment (`v0.068`, JS vocabulary addendum stage
8/10 -- see `docs/version history/v0.068.md`). See `sum.py` for the
general shape.

Exactly three names, in order: `Derive.lerp("a", "b", "t")` reads as
C++20 `std::lerp(a, b, t)` -- `a + t * (b - a)`, with `t == 0`
returning exactly `a` and `t == 1` returning exactly `b` rather than
whatever floating-point rounding `a + t * (b - a)` would otherwise
produce at those two edges.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("lerp", ...)` case (via `arklight/ir/js_numeric.py`'s `js_lerp`) so a
page's server-rendered `Bind(...)` text never disagrees with what the
client recomputes.
"""

from __future__ import annotations

NAME = "lerp"

JS_FRAGMENT = """    lerp: function (state, names, args) {
      var a = Number(state[names[0]]) || 0;
      var b = Number(state[names[1]]) || 0;
      var t = Number(state[names[2]]) || 0;
      if (t === 0) return a;
      if (t === 1) return b;
      return a + t * (b - a);
    }"""
