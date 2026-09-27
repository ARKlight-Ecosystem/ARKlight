"""
`char_at` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.charAt(index)`, with `index` a literal integer
`>= 0`. Returns `""` past the end. Indexes UTF-16 code units, so the
first half of an emoji is a lone surrogate, as in JavaScript.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("char_at", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "char_at"

JS_FRAGMENT = """    char_at: function (state, names, args) {
      return String(state[names[0]]).charAt(args.index);
    }"""
