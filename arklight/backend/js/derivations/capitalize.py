"""
`capitalize` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

Uppercases the first UTF-16 code unit and leaves the rest as it is:
`charAt(0).toUpperCase() + slice(1)`. `"hello world"` -> `"Hello world"`.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("capitalize", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "capitalize"

JS_FRAGMENT = """    capitalize: function (state, names, args) {
      var s = String(state[names[0]]);
      return s.charAt(0).toUpperCase() + s.slice(1);
    }"""
