"""
`list_includes` derivation fragment (`v0.067`, JS vocabulary addendum
stage 7/10 -- see `docs/version history/v0.067.md`). See `sum.py` for the
general shape.

`Array.prototype.includes(args.value)` over a list-valued `State(...)`.
Returns a **boolean** -- see `includes_substring.py`. `args.value` is a
literal validated at build time (a string, boolean, `null`, or finite
number); matching is strict (`===`), so `1` does not match `"1"` or
`true`. A value that is not a list never includes anything.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("list_includes", ...)` case (via `arklight/ir/js_list.py`) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "list_includes"

JS_FRAGMENT = """    list_includes: function (state, names, args) {
      var list = state[names[0]];
      return Array.isArray(list) && list.includes(args.value);
    }"""
