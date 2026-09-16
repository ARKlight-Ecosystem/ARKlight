"""
`uppercase` derivation fragment (`v0.062`, JS vocabulary addendum
stage 2/10 -- see `docs/version history/v0.062.md`). See `sum.py` for
the general shape.

A single-name string transform, same arity shape as `count`: it reads
exactly one state/computed value and coerces it to a string before
upper-casing, matching JavaScript's own `String(x).toUpperCase()`
coercion rather than throwing on a non-string value.
"""

from __future__ import annotations

NAME = "uppercase"

JS_FRAGMENT = """    uppercase: function (state, names, args) {
      return String(state[names[0]]).toUpperCase();
    }"""
