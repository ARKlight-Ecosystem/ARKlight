"""
`list_average` derivation fragment (`v0.067`, JS vocabulary addendum stage
7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

The arithmetic mean of a list-valued `State(...)`: the elements summed
left to right, divided by the list's length (`Derive.average` is the
sibling over several *named* states). See `list_min.py` for how each
element is read. An empty list, or a value that is not a list, is
`0 / 0`, so `NaN`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_average", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_average"

JS_FRAGMENT = """    list_average: function (state, names, args) {
      var list = state[names[0]];
      if (!Array.isArray(list)) { list = []; }
      var total = 0;
      for (var i = 0; i < list.length; i += 1) {
        var item = list[i];
        total += (typeof item === "number" || typeof item === "string" || typeof item === "boolean")
          ? (Number(item) || 0)
          : 0;
      }
      return total / list.length;
    }"""
