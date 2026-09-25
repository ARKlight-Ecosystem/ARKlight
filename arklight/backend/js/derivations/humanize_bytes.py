"""
`humanize_bytes` derivation fragment (v0.069, JS vocabulary addendum stage
9/10 -- see `docs/version history/v0.069.md`). See `sum.py` for the
general shape.

Binary (1024-based) byte count as a short string: `1536` -> `"1.5 KB"`,
`512` -> `"512 B"`. One decimal place, a trailing `.0` dropped, capped at `PB`.
A value that would round up to `1024` of one unit is shown in the next unit
(`1048535` -> `"1 MB"`, not `"1024 KB"`).

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("humanize_bytes", ...)` case (via `js_humanize_bytes` in `arklight/ir/js_numeric.py`) so a page's server-rendered
`Bind(...)` text never disagrees with what the client recomputes.
"""

from __future__ import annotations

NAME = "humanize_bytes"

JS_FRAGMENT = r"""    humanize_bytes: function (state, names, args) {
      var n = Number(state[names[0]]) || 0;
      if (!isFinite(n)) return String(n);
      var sign = n < 0 ? "-" : "";
      var v = Math.abs(n);
      var units = ["B", "KB", "MB", "GB", "TB", "PB"];
      if (v < 1024) return sign + String(v) + " B";
      var i = 0;
      while (v >= 1024 && i < units.length - 1) { v = v / 1024; i++; }
      if (Number(v.toFixed(1)) >= 1024 && i < units.length - 1) { v = v / 1024; i++; }
      var text = v.toFixed(1);
      if (text.slice(-2) === ".0") text = text.slice(0, -2);
      return sign + text + " " + units[i];
    }"""
