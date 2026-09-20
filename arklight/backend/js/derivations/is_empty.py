"""
`is_empty` derivation fragment (`v0.065`, JS vocabulary addendum stage
5/10 -- see `docs/version history/v0.065.md`). See `sum.py` for the
general shape.

`String(x).length === 0`. Returns a **boolean** -- see
`includes_substring.py`. Reads the *string* form, so `0` and `false`
are not empty (`"0"`, `"false"`) and `None` is `"null"`; it is meant
for text input (`Show` an empty-state message while a box is blank).

Mirrors `arklight.ir.build`'s build-time `_evaluate_derivation
("is_empty", ...)` case (via `arklight/ir/js_string.py`, which reproduces
JavaScript's UTF-16 indexing and `String(x)` coercion) so a page's
server-rendered `Bind(...)` text never disagrees with what the client
recomputes.
"""

from __future__ import annotations

NAME = "is_empty"

JS_FRAGMENT = """    is_empty: function (state, names, args) {
      return String(state[names[0]]).length === 0;
    }"""
