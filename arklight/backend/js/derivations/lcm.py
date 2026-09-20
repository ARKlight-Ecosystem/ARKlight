"""
`lcm` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

One or more names: the least common multiple of each value's
`Math.abs(Math.trunc(x))` (`0` if any value is `0`; `NaN` if any value is
non-finite). Divides before multiplying (`a / gcd * b`) to keep the
intermediate small.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("lcm", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "lcm"

JS_FRAGMENT = """    lcm: function (state, names, args) {
      var values = names.map(function (name) {
        return Number(state[name]) || 0;
      }).map(function (value) {
        return Math.abs(Math.trunc(value));
      });
      if (!values.every(isFinite)) return NaN;
      return values.reduce(function (a, b) {
        if (a === 0 || b === 0) return 0;
        var x = a;
        var y = b;
        while (y) {
          var rest = x % y;
          x = y;
          y = rest;
        }
        return a / x * b;
      });
    }"""
