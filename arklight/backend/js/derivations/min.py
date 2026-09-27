"""
`min` derivation fragment (`v0.061`, JS vocabulary addendum stage
1/10 -- see `docs/version history/v0.061.md`). See `sum.py` for the
general shape. Variadic like `sum`/`multiply` (one or more names,
order doesn't matter), but has no meaningful identity element, so
unlike `sum`'s `0`/`multiply`'s `1` fold, this reduces starting from
the first coerced value rather than a fixed seed.
"""

from __future__ import annotations

NAME = "min"

JS_FRAGMENT = """    min: function (state, names, args) {
      return names.slice(1).reduce(function (best, name) {
        return Math.min(best, Number(state[name]) || 0);
      }, Number(state[names[0]]) || 0);
    }"""
