"""
`string_length` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String.prototype.length`, in UTF-16 code units (`"😀"` is `2`) --
the same number `slice_string`/`char_at`/`pad_*` index by. Complements
`count`, which counts a list's items, not a string's characters.

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("string_length", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "string_length"

JS_FRAGMENT = """    string_length: function (state, names, args) {
      return String(state[names[0]]).length;
    }"""
