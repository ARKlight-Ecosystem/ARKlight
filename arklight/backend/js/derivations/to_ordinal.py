"""
`to_ordinal` derivation fragment (v0.069, JS vocabulary addendum stage
9/10 -- see `docs/version history/v0.069.md`). See `sum.py` for the
general shape.

`1` -> `"1st"`, `2` -> `"2nd"`, `11` -> `"11th"`. Reads one name as a
number (`Number(x) || 0`); a value that isn't a whole, finite number is returned
as its plain string with no suffix.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("to_ordinal", ...)` case (via `js_to_ordinal` in `arklight/ir/js_numeric.py`) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "to_ordinal"

JS_FRAGMENT = r"""    to_ordinal: function (state, names, args) {
      var n = Number(state[names[0]]) || 0;
      if (!isFinite(n) || Math.floor(n) !== n) return String(n);
      var a = Math.abs(n);
      var tens = a % 100;
      var last = a % 10;
      var suffix = "th";
      if (tens < 11 || tens > 13) {
        if (last === 1) suffix = "st";
        else if (last === 2) suffix = "nd";
        else if (last === 3) suffix = "rd";
      }
      return String(n) + suffix;
    }"""
