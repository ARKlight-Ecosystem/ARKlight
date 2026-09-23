"""
`list_last` derivation fragment (`v0.067`, JS vocabulary addendum stage
7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

The last element of a list-valued `State(...)`, as it is (`arr.at(-1)`,
written `list[list.length - 1]` so it also runs in browsers that predate
`at`). `null` for an empty list or a value that is not a list -- see
`list_first.py`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_last", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_last"

JS_FRAGMENT = """    list_last: function (state, names, args) {
      var list = state[names[0]];
      return Array.isArray(list) && list.length > 0 ? list[list.length - 1] : null;
    }"""
