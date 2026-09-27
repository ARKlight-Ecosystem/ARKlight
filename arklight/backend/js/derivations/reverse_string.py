"""
`reverse_string` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

Reverses by **code point**, so an emoji's surrogate pair survives:
`Array.from(s).reverse().join("")`. Not grapheme-aware -- combining
marks and joined emoji sequences are still split.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("reverse_string", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "reverse_string"

JS_FRAGMENT = """    reverse_string: function (state, names, args) {
      return Array.from(String(state[names[0]])).reverse().join("");
    }"""
