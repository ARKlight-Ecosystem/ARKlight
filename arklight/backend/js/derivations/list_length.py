"""
`list_length` derivation fragment (`v0.067`, JS vocabulary addendum stage
7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

`Array.isArray(v) ? v.length : 0` over a list-valued `State(...)`. A value
that is not a list (a string, an object, `null`, a name never given a
value) reads as an empty list, so its length is `0`; `count.py` is the
sibling that also measures strings and objects.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_length", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_length"

JS_FRAGMENT = """    list_length: function (state, names, args) {
      var list = state[names[0]];
      return Array.isArray(list) ? list.length : 0;
    }"""
