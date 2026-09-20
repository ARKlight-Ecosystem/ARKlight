"""
`gcd` derivation fragment (`v0.064`, JS vocabulary addendum stage
4/10 -- see `docs/version history/v0.064.md`). See `sum.py` for the
general shape.

One or more names: the greatest common divisor of each value's
`Math.abs(Math.trunc(x))` (`gcd(0, 0)` is `0`; `NaN` if any value is
non-finite). Euclid's algorithm on `%`, which is IEEE `fmod` in both
languages, so the build-time mirror agrees exactly.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("gcd", ...)` case (via `arklight/ir/js_numeric.py` where Python's
own `math` would raise or round differently) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "gcd"

JS_FRAGMENT = """    gcd: function (state, names, args) {
      var values = names.map(function (name) {
        return Number(state[name]) || 0;
      }).map(function (value) {
        return Math.abs(Math.trunc(value));
      });
      if (!values.every(isFinite)) return NaN;
      return values.reduce(function (a, b) {
        while (b) {
          var rest = a % b;
          a = b;
          b = rest;
        }
        return a;
      });
    }"""
