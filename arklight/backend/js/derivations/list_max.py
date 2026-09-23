"""
`list_max` derivation fragment (`v0.067`, JS vocabulary addendum stage
7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

`Math.max(...list)` over a list-valued `State(...)` -- see `list_min.py`
for how each element is read. An empty list, or a value that is not a
list, gives `-Infinity`, exactly like `Math.max()` with no arguments.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_max", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_max"

JS_FRAGMENT = """    list_max: function (state, names, args) {
      var list = state[names[0]];
      var result = -Infinity;
      if (!Array.isArray(list)) { return result; }
      for (var i = 0; i < list.length; i += 1) {
        var item = list[i];
        var number = (typeof item === "number" || typeof item === "string" || typeof item === "boolean")
          ? (Number(item) || 0)
          : 0;
        if (number > result) { result = number; }
      }
      return result;
    }"""
