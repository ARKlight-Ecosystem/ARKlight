"""
`max` derivation fragment (`v0.061`, JS vocabulary addendum stage
1/10 -- see `docs/version history/v0.061.md`). See `min.py` for the
general shape and reasoning -- this is its `Math.max` twin.
"""

from __future__ import annotations

NAME = "max"

JS_FRAGMENT = """    max: function (state, names, args) {
      return names.slice(1).reduce(function (best, name) {
        return Math.max(best, Number(state[name]) || 0);
      }, Number(state[names[0]]) || 0);
    }"""
