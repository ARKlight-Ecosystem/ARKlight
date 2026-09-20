"""
`includes_substring` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.includes(substring)`, with `substring` a literal.
Returns a **boolean**. The source proposal files it as a predicate; it
ships as a derivation (addendum `v0.065`) so the result can feed
`Show(Predicate.truthy(...))`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("includes_substring", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "includes_substring"

JS_FRAGMENT = """    includes_substring: function (state, names, args) {
      return String(state[names[0]]).includes(args.substring);
    }"""
