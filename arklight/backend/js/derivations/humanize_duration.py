"""
`humanize_duration` derivation fragment (v0.069, JS vocabulary addendum stage
9/10 -- see `docs/version history/v0.069.md`). See `sum.py` for the
general shape.

Seconds as a short, at-most-two-unit string: `45` -> `"45s"`, `90` -> `"1m 30s"`,
`8100` -> `"2h 15m"`, `90061` -> `"1d 1h"`. Whole seconds only (fractions are
floored); the second unit is dropped when it's zero.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("humanize_duration", ...)` case (via `js_humanize_duration` in `arklight/ir/js_numeric.py`) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "humanize_duration"

JS_FRAGMENT = r"""    humanize_duration: function (state, names, args) {
      var n = Number(state[names[0]]) || 0;
      if (!isFinite(n)) return String(n);
      var sign = n < 0 ? "-" : "";
      var s = Math.floor(Math.abs(n));
      if (s === 0) return "0s";
      var units = [["d", 86400], ["h", 3600], ["m", 60], ["s", 1]];
      var i = 0;
      while (Math.floor(s / units[i][1]) === 0) i++;
      var text = sign + Math.floor(s / units[i][1]) + units[i][0];
      if (i < 3) {
        var second = Math.floor((s % units[i][1]) / units[i + 1][1]);
        if (second > 0) text += " " + second + units[i + 1][0];
      }
      return text;
    }"""
