"""
`starts_with` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.startsWith(substring)`, with `substring` a literal.
Returns a **boolean** -- see `includes_substring.py`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("starts_with", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "starts_with"

JS_FRAGMENT = """    starts_with: function (state, names, args) {
      return String(state[names[0]]).startsWith(args.substring);
    }"""
