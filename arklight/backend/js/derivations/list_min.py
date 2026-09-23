"""
`list_min` derivation fragment (`v0.067`, JS vocabulary addendum stage
7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

`Math.min(...list)` over a list-valued `State(...)`, written as a loop so
a long list can't overflow the call stack. Each element is read the way
`sum.py` reads a state value, `Number(x) || 0` (`NaN` and `-0` become
`0`), except that only numbers, strings and booleans are read: `null`, a
nested list and an object count as `0`. An empty list -- or a value that
is not a list -- gives `Infinity`, exactly like `Math.min()` with no
arguments; guard it with `Show` if that would reach the page.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_min", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_min"

JS_FRAGMENT = """    list_min: function (state, names, args) {
      var list = state[names[0]];
      var result = Infinity;
      if (!Array.isArray(list)) { return result; }
      for (var i = 0; i < list.length; i += 1) {
        var item = list[i];
        var number = (typeof item === "number" || typeof item === "string" || typeof item === "boolean")
          ? (Number(item) || 0)
          : 0;
        if (number < result) { result = number; }
      }
      return result;
    }"""
