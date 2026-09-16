"""
`trim` derivation fragment (`v0.062`, JS vocabulary addendum stage
2/10 -- see `docs/version history/v0.062.md`). See `sum.py` for the
general shape.

A single-name string transform, same arity shape as `count`/
`uppercase`: it reads exactly one state/computed value, coerces it to
a string, and strips leading/trailing whitespace via JavaScript's own
`String.prototype.trim()` (Unicode-aware, matches `str.strip()`'s
default whitespace set closely enough that the Python build-time
mirror in `arklight/ir/build.py` uses plain `str.strip()`).
"""

from __future__ import annotations

NAME = "trim"

JS_FRAGMENT = """    trim: function (state, names, args) {
      return String(state[names[0]]).trim();
    }"""
