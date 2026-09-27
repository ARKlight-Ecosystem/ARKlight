"""
`list_first` derivation fragment (`v0.067`, JS vocabulary addendum stage
7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

The first element of a list-valued `State(...)`, as it is (`arr.at(0)`,
written `list[0]` so it also runs in browsers that predate `at`). An
empty list, or a value that is not a list, gives `null` rather than
`undefined`, so the result is always a value a `State(...)` could hold
and `Predicate.is_null` recognises it.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_first", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_first"

JS_FRAGMENT = """    list_first: function (state, names, args) {
      var list = state[names[0]];
      return Array.isArray(list) && list.length > 0 ? list[0] : null;
    }"""
